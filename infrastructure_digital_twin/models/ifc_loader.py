"""IFC (Industry Foundation Classes) / BIM Ingestion Manager.

Provides IFC loading, schema extraction, spatial positioning,
and a synthetic infrastructure bridge model generator for testing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd

from .twin_state import (
    AssetType,
    DigitalTwinState,
    ElementHealthStatus,
    TwinElement,
)

# Optional lazy import of ifcopenshell
try:
    import ifcopenshell
    import ifcopenshell.util.element as ifc_element_util
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False
    ifcopenshell = None


@dataclass
class IFCLoadResult:
    """Metadata summary of an ingested IFC model."""
    filepath: str
    schema: str
    project_name: str
    total_elements: int
    element_types: Dict[str, int]
    success: bool
    error_message: Optional[str] = None


class IFCManager:
    """Handles IFC file parsing, property extraction, and twin model synthesis."""

    def __init__(self):
        self.current_ifc_file = None
        self.load_metadata: Optional[IFCLoadResult] = None

    def load_ifc_file(self, filepath: str) -> IFCLoadResult:
        """Parse an IFC file on disk and return extraction statistics."""
        if not HAS_IFCOPENSHELL:
            return IFCLoadResult(
                filepath=filepath,
                schema="N/A",
                project_name="Unknown",
                total_elements=0,
                element_types={},
                success=False,
                error_message="ifcopenshell library is not available in environment.",
            )

        if not os.path.exists(filepath):
            return IFCLoadResult(
                filepath=filepath,
                schema="N/A",
                project_name="Unknown",
                total_elements=0,
                element_types={},
                success=False,
                error_message=f"File does not exist: {filepath}",
            )

        try:
            self.current_ifc_file = ifcopenshell.open(filepath)
            schema = self.current_ifc_file.schema

            # Extract project name
            projects = self.current_ifc_file.by_type("IfcProject")
            project_name = projects[0].Name if projects else os.path.basename(filepath)

            # Count major product types
            products = self.current_ifc_file.by_type("IfcProduct")
            element_types: Dict[str, int] = {}
            for prod in products:
                t = prod.is_a()
                element_types[t] = element_types.get(t, 0) + 1

            self.load_metadata = IFCLoadResult(
                filepath=filepath,
                schema=schema,
                project_name=project_name or "Unnamed Project",
                total_elements=len(products),
                element_types=element_types,
                success=True,
            )
            return self.load_metadata
        except Exception as e:
            return IFCLoadResult(
                filepath=filepath,
                schema="Unknown",
                project_name="Unknown",
                total_elements=0,
                element_types={},
                success=False,
                error_message=str(e),
            )

    def populate_twin_from_ifc(self, twin_state: DigitalTwinState) -> bool:
        """Convert elements from loaded IFC into DigitalTwinState elements."""
        if not self.current_ifc_file:
            return False

        try:
            # Common physical structural elements
            relevant_types = [
                "IfcBeam", "IfcColumn", "IfcSlab", "IfcWall",
                "IfcMember", "IfcFooting", "IfcBearing", "IfcPlate"
            ]
            count = 0
            for type_name in relevant_types:
                elements = self.current_ifc_file.by_type(type_name)
                for i, elem in enumerate(elements):
                    guid = getattr(elem, "GlobalId", f"elem_{count}")
                    name = getattr(elem, "Name", f"{type_name}_{i+1}")

                    # Map to asset classification
                    asset_type = AssetType.OTHER
                    if "column" in type_name.lower():
                        asset_type = AssetType.PIER
                    elif "slab" in type_name.lower():
                        asset_type = AssetType.DECK_SLAB
                    elif "beam" in type_name.lower():
                        asset_type = AssetType.GIRDER
                    elif "bearing" in type_name.lower():
                        asset_type = AssetType.BEARING

                    # Extract properties if available
                    psets = {}
                    if hasattr(ifcopenshell, "util") and hasattr(ifcopenshell.util, "element"):
                        try:
                            psets = ifcopenshell.util.element.get_psets(elem)
                        except Exception:
                            pass

                    # Place elements in a spaced grid if geometry coordinates aren't simplified
                    twin_element = TwinElement(
                        id=f"IFC_{guid[:8]}",
                        name=name or f"{type_name}_{i+1}",
                        asset_type=asset_type,
                        ifc_guid=guid,
                        x=float((count % 10) * 15.0),
                        y=float((count // 10) * 8.0),
                        z=0.0,
                        dx=12.0,
                        dy=3.0,
                        dz=1.5,
                        health_status=ElementHealthStatus.OPTIMAL,
                        structural_health_index=99.0,
                        properties={"type": type_name, "psets": str(list(psets.keys()))},
                    )
                    twin_state.add_element(twin_element)
                    count += 1
            return True
        except Exception as e:
            print(f"Error populating twin from IFC: {e}")
            return False

    @staticmethod
    def create_synthetic_infrastructure_model() -> DigitalTwinState:
        """Generates a high-fidelity synthetic model of a viaduct bridge with sensor nodes."""
        twin = DigitalTwinState(name="Metro Cable-Stayed Viaduct Twin (Viaduct-Span-04)")

        # 1. Abutments
        twin.add_element(
            TwinElement(
                id="ABUT-01",
                name="West Abutment Foundation",
                asset_type=AssetType.ABUTMENT,
                ifc_guid="3G4u8f01-Abut-West-001",
                x=-60.0, y=0.0, z=-4.0,
                dx=10.0, dy=14.0, dz=8.0,
                health_status=ElementHealthStatus.OPTIMAL,
                structural_health_index=97.8,
                bound_sensors=["TILT-ABUT-W1", "DISP-ABUT-W1"],
                properties={"Material": "Reinforced Concrete C45/55", "Year": 2021},
            )
        )
        twin.add_element(
            TwinElement(
                id="ABUT-02",
                name="East Abutment Foundation",
                asset_type=AssetType.ABUTMENT,
                ifc_guid="3G4u8f02-Abut-East-002",
                x=60.0, y=0.0, z=-4.0,
                dx=10.0, dy=14.0, dz=8.0,
                health_status=ElementHealthStatus.OPTIMAL,
                structural_health_index=98.5,
                bound_sensors=["TILT-ABUT-E1", "DISP-ABUT-E1"],
                properties={"Material": "Reinforced Concrete C45/55", "Year": 2021},
            )
        )

        # 2. Main Piers & Pylon Towers
        pier_configs = [
            ("PIER-01", "West Transition Pier P1", -35.0, 12.0, AssetType.PIER, 96.0, ["VIB-P1-01", "TILT-P1-01"]),
            ("PYLON-01", "Central Pylon Tower (Pylon-A)", 0.0, 36.0, AssetType.PIER, 92.4, ["VIB-PYL-01", "STRAIN-PYL-01", "TILT-PYL-01"]),
            ("PIER-02", "East Transition Pier P2", 35.0, 12.0, AssetType.PIER, 95.8, ["VIB-P2-01", "TILT-P2-01"]),
        ]

        for p_id, p_name, px, p_height, a_type, shi, sensors in pier_configs:
            status = ElementHealthStatus.OPTIMAL if shi >= 90 else ElementHealthStatus.MINOR_WARNING
            twin.add_element(
                TwinElement(
                    id=p_id,
                    name=p_name,
                    asset_type=a_type,
                    ifc_guid=f"2K9x7c0{p_id}-Pier",
                    x=px, y=0.0, z=p_height / 2.0 - 5.0,
                    dx=4.5, dy=7.0, dz=p_height,
                    health_status=status,
                    structural_health_index=shi,
                    bound_sensors=sensors,
                    properties={"Material": "High-Performance Concrete C60", "Foundation": "Deep Bored Piles"},
                )
            )

        # 3. Superstructure: Deck Slabs & Main Girders (5 spans)
        deck_spans = [
            ("SPAN-01", "Deck Span 1 (West Approach)", -47.5, 25.0, 98.0, ["STRAIN-S1-01"]),
            ("SPAN-02", "Deck Span 2 (West Main)", -17.5, 35.0, 88.5, ["STRAIN-S2-01", "ACC-S2-01"]),
            ("SPAN-03", "Deck Span 3 (East Main)", 17.5, 35.0, 94.2, ["STRAIN-S3-01", "ACC-S3-01"]),
            ("SPAN-04", "Deck Span 4 (East Approach)", 47.5, 25.0, 97.6, ["STRAIN-S4-01"]),
        ]

        for s_id, s_name, sx, slen, shi, sensors in deck_spans:
            status = ElementHealthStatus.OPTIMAL if shi >= 90 else ElementHealthStatus.MINOR_WARNING
            # Girder
            twin.add_element(
                TwinElement(
                    id=f"GIRD-{s_id[-2:]}",
                    name=f"Steel Box Girder {s_id}",
                    asset_type=AssetType.GIRDER,
                    ifc_guid=f"1M3p5a0{s_id}-Girder",
                    x=sx, y=0.0, z=5.0,
                    dx=slen, dy=6.5, dz=2.4,
                    health_status=status,
                    structural_health_index=shi,
                    bound_sensors=sensors,
                    properties={"Steel Grade": "S355NL", "Span Length (m)": slen},
                )
            )
            # Deck Slab
            twin.add_element(
                TwinElement(
                    id=f"DECK-{s_id[-2:]}",
                    name=s_name,
                    asset_type=AssetType.DECK_SLAB,
                    ifc_guid=f"1M3p5b0{s_id}-Deck",
                    x=sx, y=0.0, z=6.5,
                    dx=slen, dy=12.0, dz=0.6,
                    health_status=status,
                    structural_health_index=shi + 0.5,
                    bound_sensors=[],
                    properties={"Wearing Surface": "Polymer Modified Asphalt", "Lanes": 4},
                )
            )

        # 4. Bearings & Expansion Joints
        twin.add_element(
            TwinElement(
                id="BEAR-01",
                name="Elastomeric Pot Bearing B-01",
                asset_type=AssetType.BEARING,
                ifc_guid="4T7y1u01-Bearing-01",
                x=-35.0, y=0.0, z=1.5,
                dx=2.0, dy=3.0, dz=0.8,
                health_status=ElementHealthStatus.OPTIMAL,
                structural_health_index=96.0,
                bound_sensors=["DISP-BEAR-01"],
            )
        )
        twin.add_element(
            TwinElement(
                id="JOINT-01",
                name="Modular Expansion Joint EJ-West",
                asset_type=AssetType.EXPANSION_JOINT,
                ifc_guid="4T7y1u02-Joint-01",
                x=-55.0, y=0.0, z=6.5,
                dx=1.0, dy=12.0, dz=0.5,
                health_status=ElementHealthStatus.MINOR_WARNING,
                structural_health_index=84.2,
                bound_sensors=["DISP-JOINT-01"],
            )
        )

        return twin
