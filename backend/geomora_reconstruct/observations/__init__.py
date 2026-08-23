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
]
