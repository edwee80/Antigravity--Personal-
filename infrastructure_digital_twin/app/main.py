"""Main Streamlit Entry Point for Infrastructure Digital Twin."""

from __future__ import annotations

import os
import sys

# Ensure root directory is in Python path for modular imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import streamlit as st

from app.components import inject_custom_css, render_header, render_kpi_card
from app.visualizer import (
    create_3d_twin_figure,
    create_health_donut_chart,
    create_sensor_timeseries_chart,
)
from models.ifc_loader import HAS_IFCOPENSHELL, IFCManager
from models.twin_state import DigitalTwinState, ElementHealthStatus
from sensors.api_client import ExternalWeatherAPIClient
from sensors.mqtt_client import MQTTConfig, MQTTSensorClient
from sensors.simulator import SensorSimulator, SensorType

# Page Configuration
st.set_page_config(
    page_title="Infrastructure Digital Twin",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

# Session State Initialization
if "twin_state" not in st.session_state:
    st.session_state.twin_state = IFCManager.create_synthetic_infrastructure_model()

if "simulator" not in st.session_state:
    st.session_state.simulator = SensorSimulator(anomaly_mode=False)

if "telemetry_history" not in st.session_state:
    st.session_state.telemetry_history = st.session_state.simulator.generate_batch_history(num_points=40)

if "weather_client" not in st.session_state:
    st.session_state.weather_client = ExternalWeatherAPIClient()

if "weather_data" not in st.session_state:
    st.session_state.weather_data = st.session_state.weather_client.fetch_live_conditions()


# ==========================================
# SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.markdown("### 🛠 Twin Control Hub")
    
    # 1. Model Source
    st.markdown("#### 1. BIM / IFC Model Source")
    model_source = st.radio(
        "Select Model Ingestion:",
        ["Synthetic Viaduct (IFC4 Civil)", "Upload Custom IFC File"],
        index=0,
    )

    if model_source == "Upload Custom IFC File":
        if not HAS_IFCOPENSHELL:
            st.error("⚠️ `ifcopenshell` is not installed or enabled in this environment.")
        else:
            uploaded_file = st.file_uploader("Upload IFC model (.ifc)", type=["ifc"])
            if uploaded_file is not None:
                temp_path = os.path.join(PROJECT_ROOT, "scratch", uploaded_file.name)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                manager = IFCManager()
                result = manager.load_ifc_file(temp_path)
                if result.success:
                    st.success(f"Loaded: {result.project_name} ({result.total_elements} elements)")
                    if st.button("Apply IFC to Twin State"):
                        new_state = DigitalTwinState(name=result.project_name)
                        manager.populate_twin_from_ifc(new_state)
                        st.session_state.twin_state = new_state
                        st.rerun()
                else:
                    st.error(f"Failed to parse IFC: {result.error_message}")

    st.markdown("---")

    # 2. Sensor Simulation
    st.markdown("#### 2. IoT Sensor Simulation")
    simulate_live = st.toggle("Enable Live Telemetry Stream", value=True)
    anomaly_mode = st.toggle("Inject Heavy Load Anomaly", value=False)
    st.session_state.simulator.anomaly_mode = anomaly_mode

    if st.button("🔄 Step / Refresh Telemetry", use_container_width=True):
        # Generate new reading batch
        new_batch = []
        for s_id in st.session_state.simulator.sensor_metadata:
            rd = st.session_state.simulator.generate_current_reading(s_id)
            new_batch.append({
                "timestamp": rd.timestamp,
                "sensor_id": rd.sensor_id,
                "element_id": rd.element_id,
                "type": rd.sensor_type.value,
                "value": rd.value,
                "unit": rd.unit,
                "alarm_level": rd.alarm_level,
            })
            # If warning or critical, update twin state
            if rd.alarm_level != "NORMAL":
                st.session_state.twin_state.record_alert(
                    element_id=rd.element_id,
                    severity=rd.alarm_level,
                    message=f"Threshold exceeded on {s_id}: {rd.value} {rd.unit}",
                    sensor_id=s_id,
                )
                if rd.alarm_level == "CRITICAL":
                    st.session_state.twin_state.update_element_health(rd.element_id, shi=62.0)
                else:
                    st.session_state.twin_state.update_element_health(rd.element_id, shi=82.0)

        new_df = pd.DataFrame(new_batch)
        st.session_state.telemetry_history = pd.concat(
            [st.session_state.telemetry_history, new_df], ignore_index=True
        ).tail(300)
        st.rerun()

    st.markdown("---")

    # 3. Ambient Weather
    st.markdown("#### 3. Ambient REST Telemetry")
    if st.button("Fetch Current Weather"):
        st.session_state.weather_data = st.session_state.weather_client.fetch_live_conditions()
        st.rerun()
    st.caption(f"Source: {st.session_state.weather_data.get('source', 'REST API')}")

    st.markdown("---")

    # 4. MQTT Broker Status
    st.markdown("#### 4. MQTT Broker Gateway")
    mqtt_broker = st.text_input("Broker Address", value="broker.emqx.io")
    mqtt_port = st.number_input("Broker Port", value=1883)
    st.caption("Topic: `twin/infrastructure/viaduct/#`")
    st.info("Paho-MQTT client ready for external telemetry pub/sub.")


# ==========================================
# MAIN DASHBOARD AREA
# ==========================================
twin = st.session_state.twin_state
render_header(twin_name=twin.name, live_mode=simulate_live)

# Top KPI Metric Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
overall_shi = twin.overall_health_index()
status_color = "#10B981" if overall_shi >= 90 else ("#F59E0B" if overall_shi >= 75 else "#EF4444")
weather = st.session_state.weather_data

with kpi1:
    render_kpi_card(
        label="Overall Health Index",
        value=f"{overall_shi:.1f}%",
        subtext="Weighted Structural Integrity",
        border_color=status_color,
    )
with kpi2:
    render_kpi_card(
        label="Digital Twin Elements",
        value=str(len(twin.elements)),
        subtext="BIM IFC Structural Assets",
        border_color="#38BDF8",
    )
with kpi3:
    active_alarms = len([a for a in twin.alerts if not a.get("acknowledged", False)])
    render_kpi_card(
        label="Active Alerts",
        value=str(active_alarms),
        subtext="Threshold Breaches Logged",
        border_color="#EF4444" if active_alarms > 0 else "#10B981",
    )
with kpi4:
    wind = weather.get("wind_speed_ms", 0.0)
    temp = weather.get("ambient_temp_c", 0.0)
    render_kpi_card(
        label="Ambient Conditions",
        value=f"{temp}°C / {wind} m/s",
        subtext="Temp & Wind Speed (REST)",
        border_color="#818CF8",
    )

st.write("")

# Navigation Tabs
tab_3d, tab_telemetry, tab_inventory, tab_alerts = st.tabs([
    "🌐 3D Spatial Twin",
    "📈 Structural Telemetry (SHM)",
    "📦 BIM Asset Inventory",
    "🚨 Alarms & Events",
])

# -------------------------------------------------------------
# TAB 1: 3D SPATIAL TWIN
# -------------------------------------------------------------
with tab_3d:
    col_viz, col_status = st.columns([3, 1])

    with col_viz:
        st.markdown("##### 3D BIM Infrastructure Geometry & Sensor Mesh")
        st.caption("Rotate, pan, zoom, or hover on bridge spans, pylons, abutments, and sensor markers.")
        fig_3d = create_3d_twin_figure(twin)
        st.plotly_chart(fig_3d, use_container_width=True)

    with col_status:
        st.markdown("##### Element Health Breakdown")
        counts = twin.count_by_status()
        donut_fig = create_health_donut_chart(counts)
        st.plotly_chart(donut_fig, use_container_width=True)

        st.markdown("##### Recent Events")
        if twin.alerts:
            for alert in twin.alerts[:3]:
                sev = alert["severity"]
                c = "badge-critical" if sev == "CRITICAL" else "badge-warning"
                st.markdown(
                    f"""
                    <div style="background: rgba(30,41,59,0.6); padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; font-size: 0.85rem;">
                        <span class="status-badge {c}">{sev}</span>
                        <div style="font-weight: 600; margin-top: 4px;">{alert['element_id']} ({alert['sensor_id']})</div>
                        <div style="color: #94A3B8; font-size: 0.75rem;">{alert['message']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("All structural channels operating within nominal parameters.")

# -------------------------------------------------------------
# TAB 2: SENSOR TELEMETRY (SHM)
# -------------------------------------------------------------
with tab_telemetry:
    st.markdown("##### Real-Time Structural Health Monitoring Timeseries")
    
    sensor_options = list(st.session_state.simulator.sensor_metadata.keys())
    sel_sensor = st.selectbox("Select Active Telemetry Channel:", sensor_options, index=0)

    meta = st.session_state.simulator.sensor_metadata[sel_sensor]
    stype = meta["type"]
    threshold = st.session_state.simulator.DEFAULT_THRESHOLDS.get(stype)

    t_chart = create_sensor_timeseries_chart(
        df=st.session_state.telemetry_history,
        sensor_id=sel_sensor,
        threshold=threshold,
    )
    st.plotly_chart(t_chart, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Target Element:** `{meta['element_id']}`")
    with c2:
        st.markdown(f"**Measurement Domain:** `{stype.value}`")
    with c3:
        st.markdown(f"**Warning Threshold:** `{threshold.warning_high if threshold else 'N/A'} {meta['unit']}`")

# -------------------------------------------------------------
# TAB 3: BIM ASSET INVENTORY
# -------------------------------------------------------------
with tab_inventory:
    st.markdown("##### BIM Asset Hierarchy & Metadata")
    df_assets = twin.to_dataframe()
    if not df_assets.empty:
        st.dataframe(
            df_assets[
                ["id", "name", "asset_type", "health_status", "structural_health_index", "bound_sensors", "last_updated"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No BIM elements currently loaded.")

# -------------------------------------------------------------
# TAB 4: ALARMS & EVENTS
# -------------------------------------------------------------
with tab_alerts:
    st.markdown("##### Audit Trail & Anomaly Notification Log")
    if twin.alerts:
        df_alerts = pd.DataFrame(twin.alerts)
        st.dataframe(df_alerts, use_container_width=True, hide_index=True)
        if st.button("Acknowledge All Alerts"):
            for a in twin.alerts:
                a["acknowledged"] = True
            st.success("All alerts acknowledged.")
            st.rerun()
    else:
        st.info("Zero active alerts. Structural systems nominal.")
