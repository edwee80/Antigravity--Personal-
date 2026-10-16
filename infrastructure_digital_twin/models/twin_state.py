"""Digital Twin State and Asset Representation Models."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import pandas as pd


class ElementHealthStatus(str, Enum):
    """Health classification for structural elements."""
    OPTIMAL = "Optimal"
    MINOR_WARNING = "Minor Warning"
    ELEVATED_RISK = "Elevated Risk"
    CRITICAL = "Critical"
    OFFLINE = "Offline"


class AssetType(str, Enum):
    """Common civil infrastructure element classifications."""
    PIER = "Pier"
    DECK_SLAB = "Deck Slab"
    GIRDER = "Girder"
    STAY_CABLE = "Stay Cable"
    ABUTMENT = "Abutment"
    BEARING = "Bearing"
    EXPANSION_JOINT = "Expansion Joint"
    SENSOR_NODE = "Sensor Node"
    OTHER = "Other"


@dataclass
class TwinElement:
    """Represents an individual physical component inside the digital twin."""
    id: str
    name: str
    asset_type: AssetType
    ifc_guid: Optional[str] = None
    # Spatial positioning (center point)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    # Dimensions for bounding box / volumetric representation
    dx: float = 1.0
    dy: float = 1.0
    dz: float = 1.0
    # Health and operational indicators
    health_status: ElementHealthStatus = ElementHealthStatus.OPTIMAL
    structural_health_index: float = 98.5  # 0 to 100
    bound_sensors: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "ifc_guid": self.ifc_guid or "",
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "dx": self.dx,
            "dy": self.dy,
            "dz": self.dz,
            "health_status": self.health_status.value,
            "structural_health_index": round(self.structural_health_index, 1),
            "bound_sensors": ", ".join(self.bound_sensors),
            "last_updated": self.last_updated.strftime("%Y-%m-%d %H:%M:%S"),
        }


class DigitalTwinState:
    """Manages the full live state of the infrastructure digital twin."""

    def __init__(self, name: str = "Major River Crossing Viaduct Twin"):
        self.name = name
        self.elements: Dict[str, TwinElement] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.telemetry_history: List[Dict[str, Any]] = []

    def add_element(self, element: TwinElement) -> None:
        self.elements[element.id] = element

    def get_element(self, element_id: str) -> Optional[TwinElement]:
        return self.elements.get(element_id)

    def update_element_health(
        self, element_id: str, shi: float, status: Optional[ElementHealthStatus] = None
    ) -> None:
        element = self.get_element(element_id)
        if element:
            element.structural_health_index = max(0.0, min(100.0, shi))
            if status:
                element.health_status = status
            else:
                if shi >= 90.0:
                    element.health_status = ElementHealthStatus.OPTIMAL
                elif shi >= 75.0:
                    element.health_status = ElementHealthStatus.MINOR_WARNING
                elif shi >= 55.0:
                    element.health_status = ElementHealthStatus.ELEVATED_RISK
                else:
                    element.health_status = ElementHealthStatus.CRITICAL
            element.last_updated = datetime.datetime.now()

    def record_alert(
        self,
        element_id: str,
        severity: str,
        message: str,
        sensor_id: Optional[str] = None,
    ) -> None:
        alert = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "element_id": element_id,
            "sensor_id": sensor_id or "N/A",
            "severity": severity,
            "message": message,
            "acknowledged": False,
        }
        self.alerts.insert(0, alert)
        # Keep recent 200 alerts
        if len(self.alerts) > 200:
            self.alerts.pop()

    def overall_health_index(self) -> float:
        if not self.elements:
            return 100.0
        scores = [e.structural_health_index for e in self.elements.values()]
        return round(sum(scores) / len(scores), 1)

    def count_by_status(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in ElementHealthStatus}
        for e in self.elements.values():
            counts[e.health_status.value] += 1
        return counts

    def to_dataframe(self) -> pd.DataFrame:
        if not self.elements:
            return pd.DataFrame()
        return pd.DataFrame([e.to_dict() for e in self.elements.values()])
