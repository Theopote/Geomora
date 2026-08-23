"""Rule-based storey/bay inference from opening detections."""
from __future__ import annotations

from typing import Any

from .vlm_evidence import ArchitecturalEvidence

from .understanding.pipeline import understand_openings, understanding_to_topology

DEFAULT_STOREY_TOLERANCE = 0.08
DEFAULT_BAY_TOLERANCE = 0.10
DOOR_FLOOR_Y_MIN = 0.72


def infer_topology_from_openings(
    openings: list[dict[str, Any]],
    *,
    storey_tolerance: float = DEFAULT_STOREY_TOLERANCE,
    bay_tolerance: float = DEFAULT_BAY_TOLERANCE,
    facade_bounds: list[float] | None = None,
    architectural_evidence: ArchitecturalEvidence | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    del storey_tolerance, bay_tolerance  # adaptive tolerances in understanding_v0.1
    result, enriched = understand_openings(
        openings,
        facade_bounds=facade_bounds,
        architectural_evidence=architectural_evidence,
    )
    return understanding_to_topology(result), enriched
