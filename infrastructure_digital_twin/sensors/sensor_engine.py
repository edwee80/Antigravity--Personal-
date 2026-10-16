"""Streaming structural sensor telemetry engine.

Simulates strain gauges and inclinometers mounted on IFC elements (identified by
GlobalId) and writes every reading to SQLite.

Per element, every `interval_s` seconds (default 2 s):
    microstrain     normal range 200-350 µε
    tilt_angle_deg  normal range 0.1-0.4°

Signal model (per element):
    element-specific mean
    + slow thermal drift (sinusoid, compressed period so it is visible in a demo)
    + AR(1) correlated sensor noise
    + occasional traffic-load bumps (strain only)
    then clamped to the normal range.

Anomalies:
    `trigger_anomaly()` queues a spike of 560-680 µε (always > 550) on one element
    for the next tick(s), with a coupled tilt increase. `auto_anomaly_prob` fires
    the same trigger at random, giving intermittent spikes without manual input.

Storage:
    `TelemetryStore` wraps a single SQLite connection behind a lock, so the engine
    thread and readers (e.g. a Streamlit app) can share it safely. File databases
    use WAL mode, so other processes can read while the engine writes.

CLI (from the project root, with the .venv active):
    python -m sensors.sensor_engine                      # run until Ctrl+C
    python -m sensors.sensor_engine --duration 30 --auto-anomaly 0.15
    python -m sensors.sensor_engine --ifc model.ifc      # use 4 elements from an IFC file
    python -m sensors.sensor_engine --ifc model.ifc --guids G1 G2 G3 G4
"""

from __future__ import annotations

import argparse
import logging
import math
import random
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_INTERVAL_S = 2.0
STRAIN_RANGE = (200.0, 350.0)          # µε, normal operating band
TILT_RANGE = (0.1, 0.4)                # degrees, normal operating band
ANOMALY_THRESHOLD_UE = 550.0           # spikes are always above this
ANOMALY_STRAIN_RANGE = (560.0, 680.0)  # µε
ANOMALY_TILT_BUMP = (0.03, 0.08)       # degrees added on top of normal tilt
THERMAL_PERIOD_S = 120.0               # compressed "day" so drift shows in a short run
TRAFFIC_EVENT_PROB = 0.15              # chance per tick of a heavy-vehicle bump

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.db"
STRUCTURAL_TYPES = ("IfcBeam", "IfcColumn", "IfcSlab")


@dataclass(frozen=True)
class MonitoredElement:
    guid: str
    name: str


# Placeholder GUIDs. They match the 4-column test frame used to validate
# bim_parser.py; replace them, or pass --ifc / --guids, for a real model.
DEFAULT_ELEMENTS: tuple[MonitoredElement, ...] = (
    MonitoredElement("3loNHTCbHAqA3apjHrHOOr", "Beam B1"),
    MonitoredElement("2VCvyCrbL7Dv384mTBCmr2", "Column C1"),
    MonitoredElement("0zjz8mCYDDJuyXpTtrO22k", "Column C2"),
    MonitoredElement("2Octk93QrCl8Cj$PYoYX3m", "Slab S1"),
)


@dataclass(frozen=True)
class SensorReading:
    timestamp: datetime  # UTC
    guid: str
    element_name: str
    microstrain: float
    tilt_angle_deg: float
    is_anomaly: bool


# ---------------------------------------------------------------------------
# Thread-safe SQLite store
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,          -- ISO-8601 UTC
    guid            TEXT    NOT NULL,
    element_name    TEXT    NOT NULL,
    microstrain     REAL    NOT NULL,
    tilt_angle_deg  REAL    NOT NULL,
    is_anomaly      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_readings_guid_ts ON readings (guid, ts);
"""


class TelemetryStore:
    """SQLite-backed reading store, safe to share across threads.

    Use ":memory:" for a throwaway in-process database.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._is_memory = self.db_path == ":memory:"
        if not self._is_memory:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        with self._lock:
            if not self._is_memory:
                self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def insert_many(self, readings: Sequence[SensorReading]) -> None:
        rows = [
            (
                r.timestamp.isoformat(timespec="milliseconds"),
                r.guid,
                r.element_name,
                r.microstrain,
                r.tilt_angle_deg,
                int(r.is_anomaly),
            )
            for r in readings
        ]
        with self._lock:
            self._conn.executemany(
                "INSERT INTO readings (ts, guid, element_name, microstrain, tilt_angle_deg, is_anomaly) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            self._conn.commit()

    def to_dataframe(
        self,
        guid: Optional[str] = None,
        anomalies_only: bool = False,
        last_n: Optional[int] = None,
    ) -> pd.DataFrame:
        """Return readings in chronological order.

        last_n limits to the most recent N rows (after filtering).
        """
        where, params = [], []
        if guid:
            where.append("guid = ?")
            params.append(guid)
        if anomalies_only:
            where.append("is_anomaly = 1")
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        sql = f"SELECT * FROM readings {where_sql} ORDER BY id DESC"
        if last_n is not None:
            sql += " LIMIT ?"
            params.append(int(last_n))
        sql = f"SELECT * FROM ({sql}) ORDER BY id ASC"

        with self._lock:
            df = pd.read_sql_query(sql, self._conn, params=params)
        if not df.empty:
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            df["is_anomaly"] = df["is_anomaly"].astype(bool)
        return df

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
@dataclass
class _ChannelState:
    strain_mean: float
    tilt_mean: float
    phase: float  # thermal phase offset, so elements don't drift in lockstep
    strain_noise: float = 0.0
    tilt_noise: float = 0.0


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    return max(bounds[0], min(bounds[1], value))


class SensorEngine:
    """Generates readings for a set of IFC elements on a background thread."""

    def __init__(
        self,
        elements: Sequence[MonitoredElement] = DEFAULT_ELEMENTS,
        store: Optional[TelemetryStore] = None,
        interval_s: float = DEFAULT_INTERVAL_S,
        auto_anomaly_prob: float = 0.0,
        seed: Optional[int] = None,
        on_readings: Optional[Callable[[List[SensorReading]], None]] = None,
    ):
        if not elements:
            raise ValueError("At least one element is required")
        guids = [e.guid for e in elements]
        if len(set(guids)) != len(guids):
            raise ValueError("Element GUIDs must be unique")
        if not 0.0 <= auto_anomaly_prob <= 1.0:
            raise ValueError("auto_anomaly_prob must be between 0 and 1")

        self.elements = list(elements)
        self._by_guid = {e.guid: e for e in self.elements}
        self.store = store if store is not None else TelemetryStore()
        self.interval_s = interval_s
        self.auto_anomaly_prob = auto_anomaly_prob
        self.on_readings = on_readings

        self._rng = random.Random(seed)
        self._states: Dict[str, _ChannelState] = {
            e.guid: _ChannelState(
                strain_mean=self._rng.uniform(235.0, 290.0),
                tilt_mean=self._rng.uniform(0.18, 0.30),
                phase=self._rng.uniform(0.0, 2.0 * math.pi),
            )
            for e in self.elements
        }
        self._pending_spikes: Dict[str, int] = {}  # GUID -> remaining spike ticks
        self._tick = 0

        self._lock = threading.Lock()  # guards rng, channel state, pending spikes
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # -- anomaly injection --------------------------------------------------
    def trigger_anomaly(self, guid: Optional[str] = None, duration_ticks: int = 1) -> str:
        """Queue a >550 µε spike on an element for the next `duration_ticks` ticks.

        guid=None picks a random monitored element. Returns the GUID used.
        Safe to call from any thread (e.g. a Streamlit button callback).
        """
        if duration_ticks < 1:
            raise ValueError("duration_ticks must be >= 1")
        with self._lock:
            if guid is None:
                guid = self._rng.choice(self.elements).guid
            elif guid not in self._by_guid:
                raise KeyError(f"Unknown GUID: {guid}")
            self._pending_spikes[guid] = max(self._pending_spikes.get(guid, 0), duration_ticks)
        logger.info("Anomaly queued on %s (%s) for %d tick(s)",
                    self._by_guid[guid].name, guid, duration_ticks)
        return guid

    # -- sampling -----------------------------------------------------------
    def _sample(self, element: MonitoredElement, sim_t: float, now: datetime) -> SensorReading:
        s = self._states[element.guid]
        rng = self._rng

        thermal = math.sin(2.0 * math.pi * sim_t / THERMAL_PERIOD_S + s.phase)  # -1..1
        s.strain_noise = 0.8 * s.strain_noise + rng.gauss(0.0, 3.0)
        s.tilt_noise = 0.9 * s.tilt_noise + rng.gauss(0.0, 0.004)
        traffic = rng.uniform(15.0, 40.0) if rng.random() < TRAFFIC_EVENT_PROB else 0.0

        strain = _clamp(s.strain_mean + 20.0 * thermal + s.strain_noise + traffic, STRAIN_RANGE)
        tilt = _clamp(s.tilt_mean + 0.04 * thermal + s.tilt_noise, TILT_RANGE)

        is_anomaly = False
        remaining = self._pending_spikes.get(element.guid, 0)
        if remaining > 0:
            strain = rng.uniform(*ANOMALY_STRAIN_RANGE)
            tilt += rng.uniform(*ANOMALY_TILT_BUMP)  # coupled response, may exceed 0.4°
            is_anomaly = True
            if remaining == 1:
                del self._pending_spikes[element.guid]
            else:
                self._pending_spikes[element.guid] = remaining - 1

        return SensorReading(
            timestamp=now,
            guid=element.guid,
            element_name=element.name,
            microstrain=round(strain, 2),
            tilt_angle_deg=round(tilt, 4),
            is_anomaly=is_anomaly,
        )

    def generate_tick(self) -> List[SensorReading]:
        """Produce and store one reading per element. Usable without the thread."""
        auto_triggered = False
        with self._lock:
            if self.auto_anomaly_prob and self._rng.random() < self.auto_anomaly_prob:
                guid = self._rng.choice(self.elements).guid
                self._pending_spikes[guid] = max(self._pending_spikes.get(guid, 0), 1)
                auto_triggered = True

            sim_t = self._tick * self.interval_s
            now = datetime.now(timezone.utc)
            readings = [self._sample(e, sim_t, now) for e in self.elements]
            self._tick += 1

        if auto_triggered:
            logger.debug("Auto anomaly fired on tick %d", self._tick)
        self.store.insert_many(readings)
        return readings

    # -- background thread --------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SensorEngine", daemon=True)
        self._thread.start()

    def stop(self, timeout: Optional[float] = None) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout if timeout is not None else self.interval_s + 1.0)
            self._thread = None

    def _run(self) -> None:
        # Schedule against a monotonic clock so the 2 s cadence doesn't drift
        # by the time spent generating and writing each batch.
        next_t = time.monotonic()
        while not self._stop.is_set():
            try:
                readings = self.generate_tick()
                if self.on_readings:
                    self.on_readings(readings)
            except Exception:
                logger.exception("Sensor tick failed")
            next_t += self.interval_s
            self._stop.wait(max(0.0, next_t - time.monotonic()))

    def __enter__(self) -> "SensorEngine":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


# ---------------------------------------------------------------------------
# IFC element selection
# ---------------------------------------------------------------------------
def elements_from_ifc(
    ifc_path: str | Path,
    guids: Optional[Sequence[str]] = None,
    count: int = 4,
) -> List[MonitoredElement]:
    """Pick monitored elements from an IFC file.

    With `guids`, those exact elements are used (names read from the file).
    Otherwise the first `count` beams/columns/slabs (sorted by class, name) are used.
    """
    import ifcopenshell  # imported lazily: only needed for this function

    model = ifcopenshell.open(str(ifc_path))
    if guids:
        picked = []
        for g in guids:
            try:
                product = model.by_guid(g)
            except RuntimeError as exc:
                raise KeyError(f"GUID {g} not found in {ifc_path}") from exc
            picked.append(product)
    else:
        candidates = [p for t in STRUCTURAL_TYPES for p in model.by_type(t)]
        candidates.sort(key=lambda p: (p.is_a(), p.Name or "", p.GlobalId))
        picked = candidates[:count]
        if len(picked) < count:
            logger.warning("Only %d structural element(s) found in %s", len(picked), ifc_path)

    return [MonitoredElement(p.GlobalId, p.Name or f"{p.is_a()} {p.GlobalId[:6]}") for p in picked]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _format_tick(readings: List[SensorReading]) -> str:
    ts = readings[0].timestamp.astimezone().strftime("%H:%M:%S")
    parts = []
    for r in readings:
        flag = " !!SPIKE" if r.is_anomaly else ""
        # ASCII units: Windows consoles (cp1252) cannot encode the Greek epsilon.
        parts.append(f"{r.element_name}: {r.microstrain:6.1f}ue {r.tilt_angle_deg:.3f}deg{flag}")
    return f"[{ts}] " + " | ".join(parts)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream simulated strain/tilt telemetry to SQLite.")
    p.add_argument("--duration", type=float, default=0.0,
                   help="Seconds to run (0 = until Ctrl+C)")
    p.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_S,
                   help="Seconds between readings (default 2)")
    p.add_argument("--auto-anomaly", type=float, default=0.1,
                   help="Probability per tick of a random spike (default 0.1, 0 disables)")
    p.add_argument("--db", default=str(DEFAULT_DB_PATH),
                   help='SQLite path, or ":memory:" (default data/telemetry.db)')
    p.add_argument("--ifc", help="IFC file to take monitored elements from")
    p.add_argument("--guids", nargs="+", help="Specific element GUIDs (requires --ifc)")
    p.add_argument("--seed", type=int, help="Random seed for reproducible runs")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args(argv)

    if args.guids and not args.ifc:
        print("--guids requires --ifc", file=sys.stderr)
        return 2

    elements = elements_from_ifc(args.ifc, args.guids) if args.ifc else list(DEFAULT_ELEMENTS)
    if not elements:
        print("No structural elements to monitor.", file=sys.stderr)
        return 1

    store = TelemetryStore(args.db)
    engine = SensorEngine(
        elements,
        store=store,
        interval_s=args.interval,
        auto_anomaly_prob=args.auto_anomaly,
        seed=args.seed,
        on_readings=lambda rs: print(_format_tick(rs), flush=True),
    )

    print(f"Monitoring {len(elements)} element(s), every {args.interval}s -> {args.db}")
    for e in elements:
        print(f"  {e.guid}  {e.name}")
    print("Press Ctrl+C to stop.\n")

    engine.start()
    try:
        if args.duration > 0:
            time.sleep(args.duration)
        else:
            while True:
                time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()

    df = store.to_dataframe()
    store.close()
    spikes = int(df["is_anomaly"].sum()) if not df.empty else 0
    print(f"\nStopped. {len(df)} readings written to {args.db} ({spikes} anomalous).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
