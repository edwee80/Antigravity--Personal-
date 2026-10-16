# Quickstart Guide

This guide walks through activating the virtual environment, verifying package dependencies, and launching the Infrastructure Digital Twin interactive dashboard.

## 1. Virtual Environment Activation

The project directory includes a dedicated virtual environment in `.venv`.

### On Windows (PowerShell):
```powershell
cd "c:\Users\edwee\Documents\Edrey\Antigravity (Personal)\infrastructure_digital_twin"
.\.venv\Scripts\Activate.ps1
```

### On Windows (Command Prompt):
```cmd
cd "c:\Users\edwee\Documents\Edrey\Antigravity (Personal)\infrastructure_digital_twin"
.\.venv\Scripts\activate.bat
```

---

## 2. Verify Installed Dependencies

All core packages (`streamlit`, `ifcopenshell`, `plotly`, `pandas`, `paho-mqtt`, and `requests`) are installed. To verify:

```powershell
python -m pip list
```

---

## 3. Run the Digital Twin Dashboard

Run the Streamlit app from within the project directory:

```powershell
python -m streamlit run app/main.py
```
Or use the root convenience launcher:
```powershell
python run.py
```

The browser will open to `http://localhost:8501`.

---

## 4. Key Interactive Features to Explore

1. **3D Spatial Twin Tab**:
   - Rotate, pan, and zoom the 3D bridge structure.
   - Hover over spans, pylons, abutments, and glowing cyan sensor node diamonds.
2. **Telemetry Simulation**:
   - Toggle **Enable Live Telemetry Stream** and click **Step / Refresh Telemetry** in the sidebar.
   - Toggle **Inject Heavy Load Anomaly** to simulate severe traffic load spikes and watch element health indicators switch from Optimal to Warning/Critical!
3. **Sensor Timeseries (SHM)**:
   - Select different sensor channels (Strain on Girder 2, Vibration on Pylon, Tilt, Displacement) to monitor real-time curves against threshold lines.
4. **BIM Asset Inventory**:
   - Inspect tabular IFC properties, dimensions, and health metrics.
5. **Alarms & Event Log**:
   - Review threshold breaches and acknowledge active alarms.
