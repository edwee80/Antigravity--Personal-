# Sensor & Telemetry Specification

## 1. MQTT Topic Hierarchy

All sensor telemetry within the infrastructure mesh follows a standardized hierarchical topic structure:

```text
twin/infrastructure/{asset_id}/{element_id}/{sensor_type}/{sensor_id}
```

### Examples:
* `twin/infrastructure/viaduct_01/GIRD-02/strain/STRAIN-S2-01`
* `twin/infrastructure/viaduct_01/PYLON-01/vibration/VIB-PYL-01`
* `twin/infrastructure/viaduct_01/ABUT-01/tilt/TILT-ABUT-W1`
* `twin/infrastructure/viaduct_01/JOINT-01/displacement/DISP-JOINT-01`

---

## 2. Telemetry Payload Schema

MQTT payloads are serialized as JSON objects with the following schema:

```json
{
  "sensor_id": "STRAIN-S2-01",
  "element_id": "GIRD-02",
  "sensor_type": "Strain (microstrain)",
  "value": 248.52,
  "unit": "με",
  "timestamp": "2026-10-14T03:00:00Z",
  "quality": 100,
  "alarm_level": "NORMAL",
  "metadata": {
    "mounting_point": "Midspan Bottom Flange",
    "temperature_comp_c": 21.8
  }
}
```

---

## 3. Supported Sensor Types & Nominal Thresholds

| Sensor Type | Physical Metric | Engineering Unit | Nominal Baseline | Warning Threshold | Critical Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fiber Optic / Foil Strain Gauge** | Structural Microstrain | $\mu\epsilon$ | 180.0 – 220.0 | $\ge 350.0$ | $\ge 500.0$ |
| **Triaxial MEMS Accelerometer** | Dynamic Vibration | $m/s^2$ | 0.2 – 0.5 | $\ge 2.5$ | $\ge 4.0$ |
| **Electrolytic Inclinometer** | Pier / Pylon Angular Tilt | degrees ($^\circ$) | 0.05 – 0.15 | $\ge 0.8$ | $\ge 1.5$ |
| **LVDT / Draw-Wire Displacement** | Joint Expansion / Bearing | $mm$ | 8.0 – 12.0 | $\ge 15.0$ | $\ge 22.0$ |
| **RTD / Thermocouple** | Element Temperature | $^\circ C$ | -10.0 – 35.0 | $\ge 45.0$ | $\ge 55.0$ |
| **Ultrasonic Anemometer** | Ambient Wind Speed | $m/s$ | 3.0 – 12.0 | $\ge 20.0$ | $\ge 30.0$ |
