"""Observation Graph v0.1 — evidence layer between perception and architectural facts."""

from .models import (
    Observation,
    ObservationGraph,
    ObservationKind,
    ObservationSource,
    SemanticCandidate,
)
from .graph import ObservationGraphBuilder
from .adapters import (
    detection_result_to_observations,
    facade_row_to_observations,
    yolo_to_observations,
)
from .fusion import fuse_observation_graphs
from .vlm_adapter import vlm_evidence_to_observations
from .structural_lines import (
    detect_horizontal_structure_observations,
    horizontal_observations_to_storey_cues,
    classify_horizontal_structure_roles,
)
from .depth_discontinuities import depth_discontinuity_observations, depth_observations_to_storey_cues

__all__ = [
    "Observation",
    "ObservationGraph",
    "ObservationKind",
    "ObservationSource",
    "SemanticCandidate",
    "ObservationGraphBuilder",
    "detection_result_to_observations",
    "facade_row_to_observations",
    "yolo_to_observations",
    "fuse_observation_graphs",
    "vlm_evidence_to_observations",
    "detect_horizontal_structure_observations",
    "horizontal_observations_to_storey_cues",
    "classify_horizontal_structure_roles",
    "depth_discontinuity_observations",
    "depth_observations_to_storey_cues",
]
