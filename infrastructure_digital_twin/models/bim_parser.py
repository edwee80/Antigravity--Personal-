"""BIM parser: extract structural elements from an IFC file and render them in 3D.

Pipeline:
    1. Open the IFC file with ifcopenshell.
    2. Collect structural elements (IfcBeam, IfcColumn, IfcSlab by default;
       subtypes such as IfcSlabStandardCase are included automatically).
    3. Triangulate each element's real geometry in world coordinates using
       ifcopenshell.geom (output is always in metres, regardless of file units).
    4. Compute an axis-aligned bounding box per element from its vertices.
    5. Build a Plotly figure with one Mesh3d trace per element, keyed by GUID,
       so individual elements can be recoloured at any time.

CLI usage (from the project root):
    python -m models.bim_parser path/to/model.ifc
    python -m models.bim_parser model.ifc --html twin.html --csv elements.csv
    python -m models.bim_parser model.ifc --color-by elevation --show
"""

from __future__ import annotations

import argparse
import logging
import multiprocessing
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import ifcopenshell
import ifcopenshell.geom
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

logger = logging.getLogger(__name__)

STRUCTURAL_TYPES: tuple[str, ...] = ("IfcBeam", "IfcColumn", "IfcSlab")

DEFAULT_CLASS_COLORS: Dict[str, str] = {
    "IfcBeam": "#38BDF8",
    "IfcColumn": "#A78BFA",
    "IfcSlab": "#94A3B8",
}
FALLBACK_COLOR = "#CBD5E1"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class StructuralElement:
    """A triangulated IFC element in world coordinates (metres)."""

    guid: str
    ifc_id: int
    ifc_class: str
    name: str
    vertices: np.ndarray  # shape (N, 3)
    faces: np.ndarray  # shape (M, 3), indices into `vertices`

    @property
    def bbox_min(self) -> np.ndarray:
        return self.vertices.min(axis=0)

    @property
    def bbox_max(self) -> np.ndarray:
        return self.vertices.max(axis=0)

    @property
    def centroid(self) -> np.ndarray:
        """Centre of the bounding box (not the volumetric centroid)."""
        return (self.bbox_min + self.bbox_max) / 2.0

    @property
    def dimensions(self) -> np.ndarray:
        return self.bbox_max - self.bbox_min

    def to_record(self) -> Dict[str, object]:
        mn, mx, dims = self.bbox_min, self.bbox_max, self.dimensions
        return {
            "guid": self.guid,
            "ifc_id": self.ifc_id,
            "ifc_class": self.ifc_class,
            "name": self.name,
            "min_x": mn[0], "min_y": mn[1], "min_z": mn[2],
            "max_x": mx[0], "max_y": mx[1], "max_z": mx[2],
            "dx": dims[0], "dy": dims[1], "dz": dims[2],
            "n_vertices": len(self.vertices),
            "n_triangles": len(self.faces),
        }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class BIMParser:
    """Parses an IFC file and extracts triangulated structural elements."""

    def __init__(
        self,
        ifc_path: str | Path,
        element_types: Sequence[str] = STRUCTURAL_TYPES,
        num_threads: Optional[int] = None,
    ):
        self.path = Path(ifc_path)
        if not self.path.is_file():
            raise FileNotFoundError(f"IFC file not found: {self.path}")

        self.model = ifcopenshell.open(str(self.path))
        self.element_types = tuple(element_types)
        self.num_threads = num_threads or max(1, multiprocessing.cpu_count())

        self.elements: List[StructuralElement] = []
        # GUID -> reason, for elements that were found but could not be meshed
        self.skipped: Dict[str, str] = {}

    @property
    def schema(self) -> str:
        return self.model.schema

    def _collect_products(self) -> List[ifcopenshell.entity_instance]:
        products: Dict[int, ifcopenshell.entity_instance] = {}
        for ifc_type in self.element_types:
            try:
                for product in self.model.by_type(ifc_type):
                    products[product.id()] = product
            except RuntimeError:
                # Type does not exist in this schema (e.g. IFC4x3-only classes in IFC2x3)
                logger.warning("Type %s not present in schema %s", ifc_type, self.schema)
        return list(products.values())

    @staticmethod
    def _geometry_settings() -> ifcopenshell.geom.settings:
        settings = ifcopenshell.geom.settings()
        # Bake object placements into vertex coordinates so all elements share
        # a single global coordinate system.
        settings.set("use-world-coords", True)
        return settings

    def parse(self) -> List[StructuralElement]:
        """Triangulate all matching elements. Returns the parsed elements."""
        self.elements = []
        self.skipped = {}

        with_geometry: Dict[int, ifcopenshell.entity_instance] = {}
        for product in self._collect_products():
            if product.Representation is None:
                self.skipped[product.GlobalId] = "No geometric representation"
            else:
                with_geometry[product.id()] = product

        if not with_geometry:
            return self.elements

        iterator = ifcopenshell.geom.iterator(
            self._geometry_settings(),
            self.model,
            self.num_threads,
            include=list(with_geometry.values()),
        )

        meshed_ids: set[int] = set()
        if iterator.initialize():
            while True:
                shape = iterator.get()
                product = with_geometry.get(shape.id)
                if product is not None:
                    element = self._to_element(product, shape.geometry)
                    if element is not None:
                        self.elements.append(element)
                        meshed_ids.add(shape.id)
                if not iterator.next():
                    break

        for pid, product in with_geometry.items():
            if pid not in meshed_ids and product.GlobalId not in self.skipped:
                self.skipped[product.GlobalId] = "Geometry could not be triangulated"

        # Stable ordering: by class, then name
        self.elements.sort(key=lambda e: (e.ifc_class, e.name, e.guid))
        return self.elements

    @staticmethod
    def _to_element(product, geometry) -> Optional[StructuralElement]:
        vertices = np.asarray(geometry.verts, dtype=float).reshape(-1, 3)
        faces = np.asarray(geometry.faces, dtype=np.int64).reshape(-1, 3)
        if len(vertices) == 0 or len(faces) == 0:
            return None
        return StructuralElement(
            guid=product.GlobalId,
            ifc_id=product.id(),
            ifc_class=product.is_a(),
            name=product.Name or product.GlobalId,
            vertices=vertices,
            faces=faces,
        )

    def to_dataframe(self) -> pd.DataFrame:
        """One row per element: GUID, class, name, bounding box, mesh stats."""
        return pd.DataFrame([e.to_record() for e in self.elements])


# ---------------------------------------------------------------------------
# Plotly visualisation
# ---------------------------------------------------------------------------
def values_to_colors(
    values: Mapping[str, float],
    colorscale: str = "RdYlGn",
    cmin: Optional[float] = None,
    cmax: Optional[float] = None,
) -> Dict[str, str]:
    """Map GUID -> numeric value (e.g. health index, stress) to GUID -> colour."""
    if not values:
        return {}
    arr = np.fromiter(values.values(), dtype=float)
    lo = float(arr.min()) if cmin is None else cmin
    hi = float(arr.max()) if cmax is None else cmax
    span = (hi - lo) or 1.0
    normalised = [float(np.clip((v - lo) / span, 0.0, 1.0)) for v in values.values()]
    return dict(zip(values.keys(), sample_colorscale(colorscale, normalised)))


def _element_color(
    element: StructuralElement,
    colors: Optional[Mapping[str, str]],
) -> str:
    if colors and element.guid in colors:
        return colors[element.guid]
    return DEFAULT_CLASS_COLORS.get(element.ifc_class, FALLBACK_COLOR)


def build_mesh_figure(
    elements: Iterable[StructuralElement],
    colors: Optional[Mapping[str, str]] = None,
    values: Optional[Mapping[str, float]] = None,
    colorscale: str = "RdYlGn",
    cmin: Optional[float] = None,
    cmax: Optional[float] = None,
    value_label: str = "Value",
    opacity: float = 1.0,
    title: Optional[str] = None,
) -> go.Figure:
    """Build a 3D figure with one Mesh3d trace per element.

    Colouring, in order of precedence:
        colors : GUID -> CSS colour string (explicit per-element colours).
        values : GUID -> float, mapped through `colorscale` with a colour bar.
        default: coloured by IFC class (DEFAULT_CLASS_COLORS).

    Each trace stores the element GUID in `trace.meta`, which is what
    `recolor_figure` uses to update colours later.
    """
    elements = list(elements)
    value_colors = values_to_colors(values, colorscale, cmin, cmax) if values else {}
    resolved = {**value_colors, **(colors or {})}
    by_class_legend = not resolved

    fig = go.Figure()
    legend_seen: set[str] = set()

    for el in elements:
        v, f = el.vertices, el.faces
        mn, mx = el.bbox_min, el.bbox_max
        value_line = (
            f"{value_label}: {values[el.guid]:.2f}<br>" if values and el.guid in values else ""
        )
        hover = (
            f"<b>{el.name}</b><br>"
            f"{el.ifc_class}<br>"
            f"GUID: {el.guid}<br>"
            f"{value_line}"
            f"Min: ({mn[0]:.2f}, {mn[1]:.2f}, {mn[2]:.2f})<br>"
            f"Max: ({mx[0]:.2f}, {mx[1]:.2f}, {mx[2]:.2f})"
            "<extra></extra>"
        )
        show_legend = by_class_legend and el.ifc_class not in legend_seen
        legend_seen.add(el.ifc_class)

        fig.add_trace(
            go.Mesh3d(
                x=v[:, 0], y=v[:, 1], z=v[:, 2],
                i=f[:, 0], j=f[:, 1], k=f[:, 2],
                color=_element_color(el, resolved),
                opacity=opacity,
                flatshading=True,
                lighting=dict(ambient=0.55, diffuse=0.8, specular=0.15, roughness=0.6),
                name=el.ifc_class if by_class_legend else el.name,
                legendgroup=el.ifc_class,
                showlegend=show_legend,
                meta=el.guid,
                hovertemplate=hover,
            )
        )

    # Mesh3d with a single `color` cannot draw a colour bar, so add an
    # invisible marker trace that carries the scale.
    if values and not colors:
        arr = np.fromiter(values.values(), dtype=float)
        fig.add_trace(
            go.Scatter3d(
                x=[None], y=[None], z=[None],
                mode="markers",
                marker=dict(
                    colorscale=colorscale,
                    cmin=float(arr.min()) if cmin is None else cmin,
                    cmax=float(arr.max()) if cmax is None else cmax,
                    color=[float(arr.min())],
                    showscale=True,
                    colorbar=dict(title=value_label),
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        legend=dict(itemsizing="constant"),
        scene=dict(
            aspectmode="data",
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Z (m)",
        ),
    )
    return fig


def recolor_figure(fig: go.Figure, colors: Mapping[str, str]) -> go.Figure:
    """Update element colours in place (GUID -> colour). Unlisted elements keep theirs.

    Example:
        recolor_figure(fig, {"2O2Fr$t4X7Zf8NOew3FLOH": "#EF4444"})
    """
    def _apply(trace):
        guid = getattr(trace, "meta", None)
        if isinstance(guid, str) and guid in colors:
            trace.color = colors[guid]

    fig.for_each_trace(_apply, selector=dict(type="mesh3d"))
    return fig


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract structural elements from an IFC file.")
    p.add_argument("ifc_path", help="Path to the .ifc file")
    p.add_argument(
        "--types", nargs="+", default=list(STRUCTURAL_TYPES),
        help="IFC classes to extract (default: IfcBeam IfcColumn IfcSlab)",
    )
    p.add_argument("--csv", help="Write element table (GUID + bounding box) to this CSV path")
    p.add_argument("--html", help="Write the interactive 3D figure to this HTML path")
    p.add_argument(
        "--color-by", choices=["class", "elevation"], default="class",
        help="'class' = colour by IFC type; 'elevation' = demo value-based colouring by Z",
    )
    p.add_argument("--show", action="store_true", help="Open the figure in a browser")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args(argv)

    parser = BIMParser(args.ifc_path, element_types=args.types)
    elements = parser.parse()

    print(f"File:     {parser.path.name} (schema {parser.schema})")
    print(f"Parsed:   {len(elements)} element(s)")
    if parser.skipped:
        print(f"Skipped:  {len(parser.skipped)} element(s)")
        for guid, reason in parser.skipped.items():
            print(f"  - {guid}: {reason}")

    if not elements:
        return 1

    df = parser.to_dataframe()
    with pd.option_context("display.max_columns", None, "display.width", 160):
        print(df[["guid", "ifc_class", "name", "min_x", "min_y", "min_z",
                  "max_x", "max_y", "max_z"]].round(3).to_string(index=False))

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"CSV written to {args.csv}")

    values = None
    if args.color_by == "elevation":
        values = {e.guid: float(e.centroid[2]) for e in elements}

    fig = build_mesh_figure(
        elements,
        values=values,
        colorscale="Viridis",
        value_label="Elevation (m)",
        title=f"{parser.path.name} — {len(elements)} structural elements",
    )

    if args.html:
        fig.write_html(args.html, include_plotlyjs="cdn")
        print(f"HTML written to {args.html}")
    if args.show:
        fig.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
