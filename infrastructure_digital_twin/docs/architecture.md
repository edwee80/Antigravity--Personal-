# Infrastructure Digital Twin Architecture

## System Overview

The **Infrastructure Digital Twin** platform bridges physical civil assets (bridges, viaducts, tunnels, dams, highway corridors) with high-fidelity digital representations by fusing **Building Information Modeling (BIM / IFC)** with **real-time Internet of Things (IoT / SCADA) telemetry**.

```mermaid
graph TD
    subgraph Physical Infrastructure Asset
        S1["Strain Gauges (με)"]
        S2["Accelerometers (m/s²)"]
        S3["Inclinometers / Tilt (deg)"]
        S4["Displacement Transducers (mm)"]
        ENV["Weather Station"]
    end

    subgraph Ingestion & Communication Layer
        MQTT["Paho-MQTT Broker (paho-mqtt)"]
        REST["REST Environmental Client (requests)"]
    end

    subgraph Digital Twin Core Engine
        IFC["IFC / BIM Loader (ifcopenshell)"]
        STATE["Digital Twin State Engine (twin_state.py)"]
        ANOMALY["Anomaly & Threshold Evaluator"]
    end

    subgraph Interactive Presentation Layer
        APP["Streamlit Application (app/main.py)"]
        VIZ["Plotly 3D Spatial Visualizer (app/visualizer.py)"]
        CHART["Timeseries SHM Dashboards (plotly)"]
    end

    S1 -->|Telemetry Stream| MQTT
    S2 -->|Telemetry Stream| MQTT
    S3 -->|Telemetry Stream| MQTT
    S4 -->|Telemetry Stream| MQTT
    ENV -->|REST API| REST

    MQTT --> STATE
    REST --> STATE
    IFC -->|BIM Asset Hierarchy| STATE
    STATE --> ANOMALY
    ANOMALY --> STATE

    STATE --> APP
    APP --> VIZ
    APP --> CHART
```

## Modular Layer Breakdown

### 1. Model Layer (`/models`)
* **`ifc_loader.py`**:
  * Utilizes `ifcopenshell` to ingest IFC2x3, IFC4, and IFC4x3 infrastructure models.
  * Extracts structural entities (`IfcBeam`, `IfcColumn`, `IfcSlab`, `IfcBridge`, etc.), property sets (Psets), and geometry.
  * Supplies a synthetic civil viaduct generator for out-of-the-box evaluation without external files.
* **`twin_state.py`**:
  * Represents structural elements as `TwinElement` instances with spatial coordinates, bounding geometry, health metrics, and bound sensors.
  * Computes overall asset Structural Health Index (SHI) and tracks historical anomaly logs.

### 2. Sensor Layer (`/sensors`)
* **`mqtt_client.py`**:
  * Thread-safe MQTT client built with `paho-mqtt` supporting MQTT v3.1.1 and v5.0.
  * Listens to hierarchical topic trees (`twin/infrastructure/viaduct/#`) and decodes JSON telemetry.
* **`simulator.py`**:
  * Simulates realistic structural response incorporating traffic loads, thermal baseline drift, micro-vibrations, and dynamic live loads.
  * Includes an anomaly injection mode to stress-test warning and critical alarm thresholds.
* **`api_client.py`**:
  * Connects to external REST APIs using `requests` to fetch ambient temperature, humidity, and wind load conditions.

### 3. Application Layer (`/app`)
* **`main.py`**:
  * Streamlit web application providing tabs for 3D spatial inspection, real-time sensor analytics, BIM inventory audit, and alarm acknowledgments.
* **`visualizer.py`**:
  * Interactive 3D scene rendered in Plotly featuring 3D bounding geometry, health color heatmaps, and sensor node pins.
  * 2D timeseries graphs with configurable threshold limit lines.
* **`components.py`**:
  * Custom dark-mode UI styling and KPI metric cards.
