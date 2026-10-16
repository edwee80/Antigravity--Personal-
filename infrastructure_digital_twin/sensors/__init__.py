"""Sensors module for Infrastructure Digital Twin.

Provides MQTT client, real-time telemetry simulation, and REST API connectors.
"""

from .mqtt_client import MQTTSensorClient, MQTTConfig
from .simulator import (
    SensorSimulator,
    SensorReading,
    SensorType,
    SensorThresholds,
)
from .api_client import ExternalWeatherAPIClient

__all__ = [
    "MQTTSensorClient",
    "MQTTConfig",
    "SensorSimulator",
    "SensorReading",
    "SensorType",
    "SensorThresholds",
    "ExternalWeatherAPIClient",
]
