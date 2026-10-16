"""REST API Client for External Environmental & SCADA Telemetry."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class ExternalWeatherAPIClient:
    """Fetches ambient environmental parameters (wind, temp, humidity) via REST."""

    def __init__(self, latitude: float = 37.7749, longitude: float = -122.4194, timeout: int = 5):
        self.latitude = latitude
        self.longitude = longitude
        self.timeout = timeout
        # Public keyless endpoint from Open-Meteo
        self.endpoint = "https://api.open-meteo.com/v1/forecast"

    def fetch_live_conditions(self) -> Dict[str, Any]:
        """Queries ambient temperature and wind speed affecting the asset."""
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure",
        }
        try:
            resp = requests.get(self.endpoint, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json().get("current", {})
                return {
                    "source": "Open-Meteo REST API",
                    "ambient_temp_c": data.get("temperature_2m", 21.5),
                    "relative_humidity_pct": data.get("relative_humidity_2m", 62.0),
                    "wind_speed_ms": data.get("wind_speed_10m", 6.8),
                    "surface_pressure_hpa": data.get("surface_pressure", 1013.2),
                    "status": "ONLINE",
                }
        except Exception as e:
            logger.warning(f"Could not reach external weather API ({e}), using calibrated fallbacks.")

        # Graceful fallback data
        return {
            "source": "Calibrated Environmental Baseline (Offline Mode)",
            "ambient_temp_c": 22.4,
            "relative_humidity_pct": 58.5,
            "wind_speed_ms": 7.2,
            "surface_pressure_hpa": 1014.5,
            "status": "SIMULATED",
        }
