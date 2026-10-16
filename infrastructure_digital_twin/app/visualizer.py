"""Plotly 3D and 2D Interactive Visualizations for Infrastructure Twin."""

from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from models.twin_state import DigitalTwinState, ElementHealthStatus, TwinElement
from sensors.simulator import SensorThresholds

STATUS_COLORS = {
    ElementHealthStatus.OPTIMAL: "#10B981",       # Emerald Green
    ElementHealthStatus.MINOR_WARNING: "#F59E0B",  # Amber
    ElementHealthStatus.ELEVATED_RISK: "#F97316", # Orange
    ElementHealthStatus.CRITICAL: "#EF4444",      # Red
    ElementHealthStatus.OFFLINE: "#6B7280",       # Slate Gray
}


def _create_box_mesh(
    element: TwinElement,
) -> go.Mesh3d:
    """Constructs a 3D rectangular box mesh for an infrastructure component."""
    x0, x1 = element.x - element.dx / 2.0, element.x + element.dx / 2.0
    y0, y1 = element.y - element.dy / 2.0, element.y + element.dy / 2.0
    z0, z1 = element.z - element.dz / 2.0, element.z + element.dz / 2.0

    # 8 vertices of a cuboid
    vx = [x0, x1, x1, x0, x0, x1, x1, x0]
    vy = [y0, y0, y1, y1, y0, y0, y1, y1]
    vz = [z0, z0, z0, z0, z1, z1, z1, z1]

    # 12 triangular facets (two per box face)
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]

    color = STATUS_COLORS.get(element.health_status, "#3B82F6")

    hover_text = (
        f"<b>{element.name}</b><br>"
        f"Asset ID: {element.id}<br>"
        f"Type: {element.asset_type.value}<br>"
        f"Health Index: {element.structural_health_index:.1f}%<br>"
        f"Status: {element.health_status.value}<br>"
        f"Bound Sensors: {', '.join(element.bound_sensors) or 'None'}"
    )

    return go.Mesh3d(
        x=vx,
        y=vy,
        z=vz,
        i=i,
        j=j,
        k=k,
        color=color,
        opacity=0.88,
        flatshading=True,
        name=element.name,
        hoverinfo="text",
        text=hover_text,
    )


def create_3d_twin_figure(twin_state: DigitalTwinState) -> go.Figure:
    """Generates an interactive 3D spatial twin view with BIM components and sensors."""
    fig = go.Figure()

    # 1. Add 3D meshes for structural elements
    sensor_x, sensor_y, sensor_z, sensor_labels = [], [], [], []

    for element in twin_state.elements.values():
        mesh = _create_box_mesh(element)
        fig.add_trace(mesh)

        # If element has bound sensors, add sensor marker pin at the top surface
        if element.bound_sensors:
            for s_name in element.bound_sensors:
                sensor_x.append(element.x)
                sensor_y.append(element.y)
                sensor_z.append(element.z + (element.dz / 2.0) + 0.8)
                sensor_labels.append(
                    f"<b>Sensor: {s_name}</b><br>Mounted on: {element.name}<br>Asset: {element.id}"
                )

    # 2. Add Sensor Marker scatter pins
    if sensor_x:
        fig.add_trace(
            go.Scatter3d(
                x=sensor_x,
                y=sensor_y,
                z=sensor_z,
                mode="markers+text",
                marker=dict(
                    size=6,
                    color="#00F0FF",
                    symbol="diamond",
                    line=dict(color="#FFFFFF", width=1),
                ),
                text=[s.split("<br>")[0].replace("<b>Sensor: ", "").replace("</b>", "") for s in sensor_labels],
                textposition="top center",
                textfont=dict(color="#00F0FF", size=9),
                hoverinfo="text",
                hovertext=sensor_labels,
                name="Sensor Nodes",
            )
        )

    # 3. Modern dark digital twin layout
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=0, r=0, t=10, b=0),
        height=540,
        showlegend=False,
        scene=dict(
            xaxis=dict(title="Longitudinal Span (m)", gridcolor="#334155", showbackground=False),
            yaxis=dict(title="Transverse Deck (m)", gridcolor="#334155", showbackground=False),
            zaxis=dict(title="Elevation (m)", gridcolor="#334155", showbackground=False),
            aspectmode="data",
            camera=dict(
                eye=dict(x=-1.6, y=-2.0, z=1.2),
                up=dict(x=0, y=0, z=1),
            ),
        ),
    )
    return fig


def create_sensor_timeseries_chart(
    df: pd.DataFrame,
    sensor_id: str,
    threshold: Optional[SensorThresholds] = None,
) -> go.Figure:
    """Builds a responsive timeseries chart for a specific sensor stream."""
    sub_df = df[df["sensor_id"] == sensor_id].sort_values("timestamp")
    fig = go.Figure()

    if not sub_df.empty:
        unit = sub_df.iloc[0]["unit"]
        fig.add_trace(
            go.Scatter(
                x=sub_df["timestamp"],
                y=sub_df["value"],
                mode="lines+markers",
                line=dict(color="#38BDF8", width=2.5),
                marker=dict(size=4, color="#0284C7"),
                name=f"{sensor_id} ({unit})",
            )
        )

        # Add threshold indicator lines
        if threshold:
            if threshold.warning_high:
                fig.add_hline(
                    y=threshold.warning_high,
                    line_dash="dash",
                    line_color="#F59E0B",
                    annotation_text=f"Warning ({threshold.warning_high} {unit})",
                    annotation_position="top right",
                )
            if threshold.critical_high:
                fig.add_hline(
                    y=threshold.critical_high,
                    line_dash="dot",
                    line_color="#EF4444",
                    annotation_text=f"Critical ({threshold.critical_high} {unit})",
                    annotation_position="top right",
                )

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        height=320,
        xaxis=dict(title="Timestamp", gridcolor="#334155"),
        yaxis=dict(title="Reading Value", gridcolor="#334155"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def create_health_donut_chart(status_counts: Dict[str, int]) -> go.Figure:
    """Renders a health status distribution donut chart."""
    labels = list(status_counts.keys())
    values = list(status_counts.values())

    color_map = {
        "Optimal": "#10B981",
        "Minor Warning": "#F59E0B",
        "Elevated Risk": "#F97316",
        "Critical": "#EF4444",
        "Offline": "#6B7280",
    }
    colors = [color_map.get(lbl, "#94A3B8") for lbl in labels]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=colors),
                textinfo="label+value",
            )
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=10, b=10),
        height=240,
        showlegend=False,
    )
    return fig
