"""Infrastructure Sensor Telemetry Simulator.

Simulates civil structural health monitoring (SHM) streams with
realistic baseline drift, dynamic live loading, environmental noise,
and controllable anomaly injections.
"""

from __future__ import annotations

import datetime
import math
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import pandas as pd


class SensorType(str, Enum):
    STRAIN = "Strain (microstrain)"
    ACCELERATION = "Vibration / Acceleration (m/s²)"
    TILT = "Inclination / Tilt (deg)"
    DISPLACEMENT = "Expansion / Displacement (mm)"
    TEMPERATURE = "Temperature (°C)"
    WIND_SPEED = "Wind Speed (m/s)"


@dataclass
class SensorReading:
    sensor_id: str
    element_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime.datetime
    is_anomaly: bool = False
    alarm_level: str = "NORMAL"  # NORMAL, WARNING, CRITICAL


@dataclass
class SensorThresholds:
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None

    def evaluate(self, value: float) -> str:
        if self.critical_high is not None and value >= self.critical_high:
            return "CRITICAL"
        if self.critical_low is not None and value <= self.critical_low:
            return "CRITICAL"
        if self.warning_high is not None and value >= self.warning_high:
            return "WARNING"
        if self.warning_low is not None and value <= self.warning_low:
            return "WARNING"
        return "NORMAL"


class SensorSimulator:
    """Simulates multi-sensor civil telemetry for structural health monitoring."""

    DEFAULT_THRESHOLDS: Dict[SensorType, SensorThresholds] = {
        SensorType.STRAIN: SensorThresholds(warning_high=350.0, critical_high=500.0),
        SensorType.ACCELERATION: SensorThresholds(warning_high=2.5, critical_high=4.0),
        SensorType.TILT: SensorThresholds(warning_high=0.8, critical_high=1.5),
        SensorType.DISPLACEMENT: SensorThresholds(warning_high=15.0, critical_high=22.0),
        SensorType.TEMPERATURE: SensorThresholds(warning_high=45.0, critical_high=55.0),
        SensorType.WIND_SPEED: SensorThresholds(warning_high=20.0, critical_high=30.0),
    }

    def __init__(self, anomaly_mode: bool = False):
        self.anomaly_mode = anomaly_mode
        self._start_time = time.time()
        self.sensor_metadata: Dict[str, Dict[str, Any]] = {
            "STRAIN-S2-01": {"element_id": "GIRD-02", "type": SensorType.STRAIN, "unit": "με", "base": 210.0},
            "STRAIN-S3-01": {"element_id": "GIRD-03", "type": SensorType.STRAIN, "unit": "με", "base": 195.0},
            "ACC-S2-01": {"element_id": "DECK-02", "type": SensorType.ACCELERATION, "unit": "m/s²", "base": 0.4},
            "VIB-PYL-01": {"element_id": "PYLON-01", "type": SensorType.ACCELERATION, "unit": "m/s²", "base": 0.3},
            "TILT-PYL-01": {"element_id": "PYLON-01", "type": SensorType.TILT, "unit": "°", "base": 0.12},
            "TILT-ABUT-W1": {"element_id": "ABUT-01", "type": SensorType.TILT, "unit": "°", "base": 0.05},
            "DISP-JOINT-01": {"element_id": "JOINT-01", "type": SensorType.DISPLACEMENT, "unit": "mm", "base": 11.5},
            "DISP-BEAR-01": {"element_id": "BEAR-01", "type": SensorType.DISPLACEMENT, "unit": "mm", "base": 4.2},
        }

    def generate_current_reading(self, sensor_id: str, elapsed_offset: float = 0.0) -> SensorReading:
        meta = self.sensor_metadata.get(sensor_id)
        if not meta:
            raise ValueError(f"Unknown sensor_id: {sensor_id}")

        t = (time.time() - self._start_time) + elapsed_offset
        stype = meta["type"]
        base = meta["base"]

        # Harmonic wave + random noise
        val = base + math.sin(t * 0.4) * (base * 0.1) + random.uniform(-base * 0.03, base * 0.03)

        # Periodic heavy vehicle / live traffic pulse
        if random.random() < 0.12:
            val += base * random.uniform(0.15, 0.35)

        # If anomaly mode is active or user triggers structural distress
        if self.anomaly_mode and ("S2" in sensor_id or "JOINT" in sensor_id):
            val += base * 0.75  # Spike past warning/critical thresholds

        val = round(val, 3)
        threshold = self.DEFAULT_THRESHOLDS.get(stype, SensorThresholds())
        alarm_level = threshold.evaluate(val)

        return SensorReading(
            sensor_id=sensor_id,
            element_id=meta["element_id"],
            sensor_type=stype,
            value=val,
            unit=meta["unit"],
            timestamp=datetime.datetime.now() - datetime.timedelta(seconds=-elapsed_offset),
            is_anomaly=(alarm_level != "NORMAL"),
            alarm_level=alarm_level,
        )

    def generate_batch_history(self, num_points: int = 50, step_seconds: int = 5) -> pd.DataFrame:
        """Generates historical time series for all sensors."""
        records = []
        for i in range(num_points, 0, -1):
            offset = -float(i * step_seconds)
            for sensor_id in self.sensor_metadata:
                reading = self.generate_current_reading(sensor_id, elapsed_offset=offset)
                records.append({
                    "timestamp": reading.timestamp,
                    "sensor_id": reading.sensor_id,
                    "element_id": reading.element_id,
                    "type": reading.sensor_type.value,
                    "value": reading.value,
                    "unit": reading.unit,
                    "alarm_level": reading.alarm_level,
                })
        return pd.DataFrame(records)
