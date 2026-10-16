"""Paho-MQTT Ingestion Client for Structural Health Sensors."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    broker: str = "broker.emqx.io"
    port: int = 1883
    client_id: str = "infra_twin_sub_01"
    topic_prefix: str = "twin/infrastructure/viaduct/#"
    keepalive: int = 60
    username: Optional[str] = None
    password: Optional[str] = None


class MQTTSensorClient:
    """Thread-safe MQTT client for receiving real-time sensor streams."""

    def __init__(self, config: Optional[MQTTConfig] = None):
        self.config = config or MQTTConfig()
        self.client: Optional[mqtt.Client] = None
        self.is_connected: bool = False
        self.message_buffer: List[Dict[str, Any]] = []
        self._custom_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_on_telemetry_received(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._custom_callback = callback

    def connect(self) -> bool:
        """Connects to the configured MQTT broker asynchronously."""
        try:
            # Paho MQTT 2.0+ standard callback version
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.config.client_id,
            )

            if self.config.username and self.config.password:
                self.client.username_pw_set(self.config.username, self.config.password)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            self.client.connect_async(self.config.broker, self.config.port, self.config.keepalive)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to initiate MQTT connection: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False

    def publish_reading(self, topic: str, payload: Dict[str, Any]) -> bool:
        if not self.client or not self.is_connected:
            return False
        try:
            res = self.client.publish(topic, json.dumps(payload), qos=1)
            return res.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}")
            return False

    def get_recent_messages(self, count: int = 20) -> List[Dict[str, Any]]:
        return self.message_buffer[-count:]

    # Callbacks
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.is_connected = True
            logger.info(f"Connected to MQTT broker {self.config.broker}:{self.config.port}")
            client.subscribe(self.config.topic_prefix)
        else:
            self.is_connected = False
            logger.warning(f"Connection failed with code {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.is_connected = False
        logger.info(f"Disconnected from MQTT broker: {reason_code}")

    def _on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str)
            data["_topic"] = msg.topic
            self.message_buffer.append(data)
            if len(self.message_buffer) > 500:
                self.message_buffer.pop(0)

            if self._custom_callback:
                self._custom_callback(data)
        except Exception as e:
            logger.debug(f"Failed to parse payload on {msg.topic}: {e}")
