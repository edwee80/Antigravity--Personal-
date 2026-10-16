"""Infrastructure Digital Twin - Real-Time 3D BIM & SHM Dashboard.

Features:
- Main Panel: 3D IFC structural model (via IfcOpenShell & Plotly Mesh3d) with
  dynamic near real-time coloring:
    * Green: Normal (<= 400 microstrain)
    * Amber: Warning (> 400 microstrain)
    * Red:   Critical (> 500 microstrain)
- Sidebar: Live metric cards, controls, and rolling 60-second time-series line chart
  for the selected structural element.
- Auto-refresh powered by Streamlit's native `@st.fragment(run_every=...)`.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from models.bim_parser import BIMParser, StructuralElement
from sensors.sensor_engine import (
    DEFAULT_ELEMENTS,
    DEFAULT_INTERVAL_S,
    MonitoredElement,
    SensorEngine,
    TelemetryStore,
)

# ---------------------------------------------------------------------------
# Path & Configuration Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_IFC_PATH = PROJECT_ROOT / "data" / "sample_frame.ifc"
DB_PATH = PROJECT_ROOT / "data" / "telemetry.db"

# Color constants matching civil engineering SHM specifications
COLOR_NORMAL = "#10B981"    # Emerald Green (<= 400 ue)
COLOR_WARNING = "#F59E0B"   # Amber (> 400 ue)
COLOR_CRITICAL = "#EF4444"  # Red (> 500 ue)
COLOR_UNMONITORED = "#64748B"  # Slate Gray for uninstrumented members

THRESHOLD_WARNING = 400.0
THRESHOLD_CRITICAL = 500.0

st.set_page_config(
    page_title="Infrastructure Digital Twin",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Cached IFC BIM Model Loader
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Parsing IFC geometry...")
def load_ifc_model(ifc_file_path: str) -> List[StructuralElement]:
    """Parse real 3D geometry from IFC file using IfcOpenShell (cached)."""
    p = Path(ifc_file_path)
    if not p.is_file():
        return []
    parser = BIMParser(p)
    return parser.parse()


def get_element_status(strain: Optional[float]) -> tuple[str, str]:
    """Returns (status_label, hex_color) based on microstrain reading."""
    if strain is None:
        return "UNMONITORED", COLOR_UNMONITORED
    if strain > THRESHOLD_CRITICAL:
        return "CRITICAL", COLOR_CRITICAL
    if strain > THRESHOLD_WARNING:
        return "WARNING", COLOR_WARNING
    return "NORMAL", COLOR_NORMAL


# ---------------------------------------------------------------------------
# Background Telemetry Engine Management
# ---------------------------------------------------------------------------
def init_telemetry_engine() -> tuple[TelemetryStore, SensorEngine]:
    """Initialize or retrieve the background sensor telemetry engine."""
    if "telemetry_store" not in st.session_state:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        st.session_state.telemetry_store = TelemetryStore(DB_PATH)

    store: TelemetryStore = st.session_state.telemetry_store

    if "sensor_engine" not in st.session_state:
        engine = SensorEngine(
            elements=DEFAULT_ELEMENTS,
            store=store,
            interval_s=DEFAULT_INTERVAL_S,
            auto_anomaly_prob=0.08,
            seed=42,
        )
        # Seed initial history if DB has very few records
        if store.count() < 15:
            for _ in range(25):
                engine.generate_tick()
        engine.start()
        st.session_state.sensor_engine = engine

    return store, st.session_state.sensor_engine


# ---------------------------------------------------------------------------
# 3D Model Plotly Mesh Generator
# ---------------------------------------------------------------------------
def build_twin_3d_figure(
    elements: List[StructuralElement],
    current_strains: Dict[str, float],
    current_tilts: Dict[str, float],
    selected_guid: Optional[str] = None,
) -> go.Figure:
    """Builds interactive 3D spatial twin with per-element dynamic colors."""
    fig = go.Figure()

    for el in elements:
        v, f = el.vertices, el.faces
        mn, mx = el.bbox_min, el.bbox_max
        strain = current_strains.get(el.guid)
        tilt = current_tilts.get(el.guid)
        status_label, color = get_element_status(strain)

        is_selected = (el.guid == selected_guid)
        opacity = 1.0 if (not selected_guid or is_selected) else 0.82

        # Telemetry hover annotation
        strain_str = f"{strain:.1f} µε" if strain is not None else "N/A (unmonitored)"
        tilt_str = f"{tilt:.3f}°" if tilt is not None else "N/A"
        selection_flag = " 🎯 [SELECTED]" if is_selected else ""

        hover_text = (
            f"<b>{el.name}</b>{selection_flag}<br>"
            f"Type: {el.ifc_class}<br>"
            f"GUID: <code>{el.guid}</code><br>"
            f"Status: <b>{status_label}</b><br>"
            f"Microstrain: <b>{strain_str}</b><br>"
            f"Tilt: <b>{tilt_str}</b><br>"
            f"Dimensions: {el.dimensions[0]:.2f}m × {el.dimensions[1]:.2f}m × {el.dimensions[2]:.2f}m"
            "<extra></extra>"
        )

        fig.add_trace(
            go.Mesh3d(
                x=v[:, 0],
                y=v[:, 1],
                z=v[:, 2],
                i=f[:, 0],
                j=f[:, 1],
                k=f[:, 2],
                color=color,
                opacity=opacity,
                flatshading=True,
                lighting=dict(ambient=0.6, diffuse=0.8, specular=0.2, roughness=0.5),
                name=el.name,
                meta=el.guid,
                hovertemplate=hover_text,
                showlegend=False,
            )
        )

    # Invisible anchor traces for a permanent status legend in 3D
    legend_entries = [
        ("Normal (<= 400 µε)", COLOR_NORMAL),
        ("Warning (> 400 µε)", COLOR_WARNING),
        ("Critical (> 500 µε)", COLOR_CRITICAL),
        ("Unmonitored", COLOR_UNMONITORED),
    ]
    for label, col in legend_entries:
        fig.add_trace(
            go.Scatter3d(
                x=[None],
                y=[None],
                z=[None],
                mode="markers",
                marker=dict(size=10, color=col, symbol="square"),
                name=label,
                showlegend=True,
            )
        )

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=0, r=0, t=10, b=0),
        height=580,
        uirevision="twin_camera_persistent_state",  # Preserves camera angle during live refreshes!
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor="rgba(15, 23, 42, 0.7)",
            bordercolor="rgba(255, 255, 255, 0.1)",
            borderwidth=1,
            itemsizing="constant",
        ),
        scene=dict(
            aspectmode="data",
            xaxis=dict(title="X (m)", gridcolor="#334155", showbackground=False),
            yaxis=dict(title="Y (m)", gridcolor="#334155", showbackground=False),
            zaxis=dict(title="Z (m)", gridcolor="#334155", showbackground=False),
            camera=dict(
                eye=dict(x=-1.8, y=-2.2, z=1.4),
                up=dict(x=0, y=0, z=1),
            ),
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# 60-Second Rolling Time-Series Line Chart Generator
# ---------------------------------------------------------------------------
def build_rolling_60s_chart(
    df_window: pd.DataFrame,
    element_name: str,
) -> go.Figure:
    """Builds a rolling 60-second time-series chart with warning/critical threshold lines."""
    fig = go.Figure()

    if not df_window.empty:
        # Sort chronologically
        df_sorted = df_window.sort_values("ts")

        # Dynamic marker colors per point based on strain
        point_colors = [
            COLOR_CRITICAL if s > THRESHOLD_CRITICAL
            else (COLOR_WARNING if s > THRESHOLD_WARNING else COLOR_NORMAL)
            for s in df_sorted["microstrain"]
        ]

        # Telemetry line
        fig.add_trace(
            go.Scatter(
                x=df_sorted["ts"],
                y=df_sorted["microstrain"],
                mode="lines+markers",
                name="Microstrain (µε)",
                line=dict(color="#38BDF8", width=2.5),
                marker=dict(size=7, color=point_colors, line=dict(color="#FFFFFF", width=1)),
                hovertemplate="<b>%{y:.1f} µε</b><br>%{x|%H:%M:%S}<extra></extra>",
            )
        )

        # Threshold horizontal lines
        fig.add_hline(
            y=THRESHOLD_WARNING,
            line_dash="dash",
            line_color=COLOR_WARNING,
            line_width=1.8,
            annotation_text=f"Warning ({int(THRESHOLD_WARNING)} µε)",
            annotation_position="top right",
            annotation_font=dict(color=COLOR_WARNING, size=11),
        )
        fig.add_hline(
            y=THRESHOLD_CRITICAL,
            line_dash="dot",
            line_color=COLOR_CRITICAL,
            line_width=2.0,
            annotation_text=f"Critical ({int(THRESHOLD_CRITICAL)} µε)",
            annotation_position="top right",
            annotation_font=dict(color=COLOR_CRITICAL, size=11),
        )

        # Set sensible Y axis bounds with headroom
        max_val = max(float(df_sorted["microstrain"].max()), THRESHOLD_CRITICAL + 50.0)
        min_val = min(float(df_sorted["microstrain"].min()), 180.0)
        y_range = [min_val - 20, max_val + 40]
    else:
        y_range = [150, 650]

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=25, b=20),
        height=260,
        showlegend=False,
        uirevision="chart_rolling_time",
        xaxis=dict(
            title="",
            gridcolor="#334155",
            tickformat="%H:%M:%S",
            showgrid=True,
        ),
        yaxis=dict(
            title="Strain (µε)",
            gridcolor="#334155",
            range=y_range,
            showgrid=True,
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# MAIN APPLICATION WORKFLOW
# ---------------------------------------------------------------------------
def main():
    store, engine = init_telemetry_engine()

    # Model resolution
    ifc_path = DEFAULT_IFC_PATH
    if not ifc_path.is_file():
        st.error(f"Sample IFC file not found at `{ifc_path}`. Run generation script.")
        return

    elements = load_ifc_model(str(ifc_path))
    if not elements:
        st.warning("No structural elements extracted from IFC model.")
        return

    # Element mapping (GUID -> StructuralElement)
    elements_by_guid = {e.guid: e for e in elements}
    monitored_guids = [e.guid for e in DEFAULT_ELEMENTS if e.guid in elements_by_guid]

    # Available elements for sidebar selector
    selector_options = monitored_guids + [g for g in elements_by_guid if g not in monitored_guids]
    selector_labels = {
        g: f"{elements_by_guid[g].name} ({elements_by_guid[g].ifc_class})"
        + (" 📡" if g in monitored_guids else "")
        for g in selector_options
    }

    # -----------------------------------------------------------------------
    # TOP HEADER & CONTROL ROW
    # -----------------------------------------------------------------------
    col_title, col_ctrl = st.columns([3, 1])
    with col_title:
        st.title("🌉 Infrastructure Digital Twin")
        st.caption("Real-Time 3D BIM Structural Health Monitoring (SHM) • Industry Foundation Classes (IFC4)")

    with col_ctrl:
        refresh_rate = st.selectbox(
            "Auto-Refresh Cadence",
            options=[1.0, 2.0, 3.0, 5.0],
            index=1,
            format_func=lambda s: f"Every {int(s)} seconds",
            help="Polling rate for live telemetry and 3D color updates.",
        )

    # -----------------------------------------------------------------------
    # SIDEBAR CONTROLS & ELEMENT SELECTION
    # -----------------------------------------------------------------------
    with st.sidebar:
        st.header(":material/sensors: Monitored Element")
        
        selected_guid = st.selectbox(
            "Select Structural Component:",
            options=selector_options,
            format_func=lambda g: selector_labels[g],
            index=0,
            help="Choose an element to inspect live telemetry and rolling trends.",
        )

        st.divider()
        st.subheader(":material/bolt: Anomaly Injection")
        st.caption("Inject controlled microstrain spikes to stress-test warning/critical thresholds:")

        btn_crit = st.button("🚨 Inject Critical Spike (>550 µε)", width="stretch")
        btn_warn = st.button("⚠️ Inject Warning Spike (>420 µε)", width="stretch")

        if btn_crit:
            target = engine.trigger_anomaly(guid=selected_guid, duration_ticks=2)
            st.toast(f"Critical anomaly queued on {elements_by_guid[target].name}!", icon="🚨")

        if btn_warn:
            # Inject moderate spike into pending spikes
            with engine._lock:
                engine._pending_spikes[selected_guid] = 2
                # Temporarily calibrate anomaly range to warning level
                orig_range = engine._states[selected_guid].strain_mean
                engine._states[selected_guid].strain_mean = 440.0
            st.toast(f"Warning spike injected on {elements_by_guid[selected_guid].name} (~440 µε)!", icon="⚠️")

    # -----------------------------------------------------------------------
    # STREAMLIT FRAGMENT: NEAR REAL-TIME POLLING & RENDERING
    # -----------------------------------------------------------------------
    # Only this fragment reruns every `refresh_rate` seconds, preventing
    # full-page flashes or resetting widget focus!
    @st.fragment(run_every=refresh_rate)
    def render_live_digital_twin(current_selected_guid: str):
        # 1. Fetch recent readings
        # Pull enough rows to comfortably cover rolling 60 seconds
        df_all = store.to_dataframe(last_n=250)

        # 2. Extract latest values per GUID
        current_strains: Dict[str, float] = {}
        current_tilts: Dict[str, float] = {}
        prev_strains: Dict[str, float] = {}
        prev_tilts: Dict[str, float] = {}

        if not df_all.empty:
            for g in monitored_guids:
                df_g = df_all[df_all["guid"] == g].sort_values("ts")
                if not df_g.empty:
                    current_strains[g] = float(df_g.iloc[-1]["microstrain"])
                    current_tilts[g] = float(df_g.iloc[-1]["tilt_angle_deg"])
                    if len(df_g) >= 2:
                        prev_strains[g] = float(df_g.iloc[-2]["microstrain"])
                        prev_tilts[g] = float(df_g.iloc[-2]["tilt_angle_deg"])

        # 3. Main Panel: Structural Model & Status Banners
        # Quick KPI Status Counters
        n_normal = sum(1 for s in current_strains.values() if s <= THRESHOLD_WARNING)
        n_warn = sum(1 for s in current_strains.values() if THRESHOLD_WARNING < s <= THRESHOLD_CRITICAL)
        n_crit = sum(1 for s in current_strains.values() if s > THRESHOLD_CRITICAL)

        with st.container():
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Monitored Assets", f"{len(monitored_guids)} / {len(elements)}", border=True)
            k2.metric("Normal", f"{n_normal}", delta=None, border=True)
            k3.metric("Warning (>400 µε)", f"{n_warn}", delta=None, border=True)
            k4.metric("Critical (>500 µε)", f"{n_crit}", delta=None, border=True)

        st.subheader("3D Spatial Twin (Plotly Mesh)")
        fig_3d = build_twin_3d_figure(
            elements=elements,
            current_strains=current_strains,
            current_tilts=current_tilts,
            selected_guid=current_selected_guid,
        )
        st.plotly_chart(fig_3d, width="stretch")

        # 4. Sidebar: Metrics and 60-second Rolling Time-Series
        selected_elem = elements_by_guid.get(current_selected_guid)
        sel_strain = current_strains.get(current_selected_guid)
        sel_prev_strain = prev_strains.get(current_selected_guid)
        sel_tilt = current_tilts.get(current_selected_guid)
        sel_prev_tilt = prev_tilts.get(current_selected_guid)
        status_label, status_col = get_element_status(sel_strain)

        with st.sidebar:
            st.divider()
            st.markdown(f"### Live Metrics: **{selected_elem.name if selected_elem else ''}**")
            
            # Status Badge Pill
            st.markdown(
                f"""
                <div style="background-color: {status_col}22; border: 1.5px solid {status_col};
                            border-radius: 8px; padding: 6px 12px; text-align: center;
                            font-weight: 700; color: {status_col}; margin-bottom: 12px;
                            letter-spacing: 0.05em;">
                    STATUS: {status_label}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Strain Metric Card
            if sel_strain is not None:
                delta_strain = f"{(sel_strain - sel_prev_strain):+.1f} µε" if sel_prev_strain else None
                st.metric(
                    label="Microstrain",
                    value=f"{sel_strain:.1f} µε",
                    delta=delta_strain,
                    border=True,
                )
            else:
                st.metric(label="Microstrain", value="No Sensor Bound", border=True)

            # Tilt Metric Card
            if sel_tilt is not None:
                delta_tilt = f"{(sel_tilt - sel_prev_tilt):+.3f}°" if sel_prev_tilt else None
                st.metric(
                    label="Inclination / Tilt",
                    value=f"{sel_tilt:.3f}°",
                    delta=delta_tilt,
                    border=True,
                )
            else:
                st.metric(label="Inclination / Tilt", value="N/A", border=True)

            # 60-Second Rolling Window Time-Series Chart
            st.markdown("#### Rolling 60s Microstrain Trend")
            if not df_all.empty and sel_strain is not None:
                # Filter to selected element and rolling 60 seconds
                cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)
                df_elem = df_all[df_all["guid"] == current_selected_guid]
                df_60s = df_elem[df_elem["ts"] >= cutoff]

                # Fallback to last 20 readings if timestamps are slightly skewed
                if len(df_60s) < 3:
                    df_60s = df_elem.tail(20)

                chart_fig = build_rolling_60s_chart(df_60s, selected_elem.name if selected_elem else "")
                st.plotly_chart(chart_fig, width="stretch")
            else:
                st.info("Element has no active sensor bindings.")

    # Call the auto-refreshing fragment
    render_live_digital_twin(selected_guid)


if __name__ == "__main__":
    main()
