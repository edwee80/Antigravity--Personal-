# Infrastructure Digital Twin 🌉

A modular, real-time **Infrastructure Digital Twin** platform for civil infrastructure monitoring (viaducts, bridges, tunnels, highways). Integrates **BIM / IFC models** (via `ifcopenshell`) with live **IoT & SCADA telemetry streams** (via `paho-mqtt` & `requests`) and interactive **3D spatial visualization** (via `plotly` & `streamlit`).

---

## 📁 Modular Directory Structure

```text
infrastructure_digital_twin/
├── .venv/               # Isolated Python virtual environment
├── requirements.txt     # Python package requirements
├── run.py               # Convenience application launcher
├── .gitignore           # Git ignore configuration
├── .env.example         # Environment variables template
│
├── models/              # BIM / IFC & Digital Twin State Models
│   ├── __init__.py      # Package exports
│   ├── ifc_loader.py    # IFC parser (ifcopenshell) & synthetic civil model generator
│   └── twin_state.py    # Asset hierarchy, health indices, and alert states
│
├── sensors/             # IoT Sensor Mesh, MQTT & REST Ingestion
│   ├── __init__.py      # Package exports
│   ├── mqtt_client.py   # Paho-MQTT client for real-time sensor streams
│   ├── simulator.py     # Structural health monitoring (SHM) telemetry simulator
│   └── api_client.py    # REST client for ambient environmental conditions
│
├── app/                 # Interactive Dashboard & Visualizations
│   ├── __init__.py      # Package exports
│   ├── main.py          # Streamlit digital twin multi-tab application
│   ├── visualizer.py    # 3D spatial twin & 2D timeseries charts (Plotly)
│   └── components.py    # Glassmorphism UI cards, badges, and dark styling
│
└── docs/                # Architecture & Specifications
    ├── README.md        # Documentation index
    ├── architecture.md  # System architecture & Mermaid flow diagram
    ├── sensor_spec.md   # MQTT topic hierarchy & JSON telemetry schema
    └── quickstart.md    # Step-by-step setup and user walkthrough
```

---

## 🚀 Quick Start

### 1. Activate the Virtual Environment

**Windows PowerShell:**
```powershell
cd "infrastructure_digital_twin"
.\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**
```cmd
cd "infrastructure_digital_twin"
.\.venv\Scripts\activate.bat
```

### 2. Dependencies

The virtual environment comes pre-configured with all required dependencies:
* `streamlit>=1.30.0`
* `ifcopenshell>=0.8.0`
* `plotly>=5.18.0`
* `pandas>=2.0.0`
* `paho-mqtt>=2.0.0`
* `requests>=2.31.0`

To reinstall or update dependencies:
```powershell
python -m pip install -r requirements.txt
```

### 3. Launch the Application

```powershell
python run.py
```
*Or directly via Streamlit:*
```powershell
python -m streamlit run app/main.py
```

The browser will open to `http://localhost:8501`.

---

## 🌟 Key Capabilities

1. **Interactive 3D Spatial Twin**:
   - Inspect 3D physical geometries of piers, deck spans, steel box girders, bearings, abutments, and expansion joints.
   - Elements are color-coded in real-time according to their **Structural Health Index (SHI)**:
     - 🟢 **Optimal** ($\ge 90\%$)
     - 🟡 **Minor Warning** ($75\% - 89\%$)
     - 🟠 **Elevated Risk** ($55\% - 74\%$)
     - 🔴 **Critical** ($< 55\%$)
2. **Real-Time Sensor Telemetry Mesh**:
   - Live simulated or MQTT-streamed sensors: Strain Gauges ($\mu\epsilon$), Vibration ($m/s^2$), Inclinometers ($^\circ$), and Joint Displacement ($mm$).
   - Dynamic anomaly injection mode to simulate severe traffic load events and trigger automated threshold alerts.
3. **BIM / IFC Extensibility**:
   - Built-in IFC loader using `ifcopenshell` supporting upload and ingestion of custom `.ifc` models.
4. **Ambient Environmental Context**:
   - Queries real-time wind speed, temperature, and atmospheric pressure using the REST API client.
5. **Auditable Alarm Management**:
   - Comprehensive audit trail of threshold breaches with alert acknowledgment workflow.
