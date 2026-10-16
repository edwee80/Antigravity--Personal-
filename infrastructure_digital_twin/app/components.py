"""Reusable Streamlit UI Components and Modern Styling."""

from __future__ import annotations

import streamlit as st


def inject_custom_css() -> None:
    """Injects high-end futuristic dark theme CSS into Streamlit."""
    st.markdown(
        """
        <style>
        /* Modern Digital Twin Glassmorphism & Accent Styles */
        .main-header {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
        }
        .twin-title {
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }
        .twin-subtitle {
            color: #94A3B8;
            font-size: 0.95rem;
            margin: 0;
        }
        .kpi-card {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: all 0.2s ease-in-out;
        }
        .kpi-card:hover {
            border-color: rgba(56, 189, 248, 0.4);
            transform: translateY(-2px);
        }
        .kpi-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94A3B8;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 1.7rem;
            font-weight: 700;
            color: #F8FAFC;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .badge-optimal { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-warning { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-critical { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(twin_name: str, live_mode: bool = True) -> None:
    """Renders the top digital twin control banner."""
    status_tag = (
        '<span class="status-badge badge-optimal">● LIVE TELEMETRY SYNC</span>'
        if live_mode
        else '<span class="status-badge badge-warning">STATIC SNAPSHOT</span>'
    )
    st.markdown(
        f"""
        <div class="main-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="twin-title">Infrastructure Digital Twin</div>
                    <div class="twin-subtitle">Asset: {twin_name} &bull; BIM / IFC4 &bull; IoT Sensor Mesh</div>
                </div>
                <div>{status_tag}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, subtext: str = "", border_color: str = "#38BDF8") -> None:
    """Renders a styled KPI indicator card."""
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left: 4px solid {border_color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
