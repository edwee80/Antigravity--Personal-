"""Models module for Infrastructure Digital Twin.

Contains IFC/BIM parser and digital twin spatial & element state models.
"""

from .ifc_loader import IFCManager, IFCLoadResult
from .twin_state import (
    TwinElement,
    DigitalTwinState,
    ElementHealthStatus,
    AssetType,
)

__all__ = [
    "IFCManager",
    "IFCLoadResult",
    "TwinElement",
    "DigitalTwinState",
    "ElementHealthStatus",
    "AssetType",
]
