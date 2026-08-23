from __future__ import annotations

from .models import Observation, ObservationGraph, ObservationKind, ObservationSource


class ObservationGraphBuilder:
    def __init__(self, photo_id: str, image_width: int, image_height: int) -> None:
        self._photo_id = photo_id
        self._image_width = image_width
        self._image_height = image_height
        self._observations: list[Observation] = []
        self._counter = 0

    def add(self, observation: Observation) -> Observation:
        self._observations.append(observation)
        return observation

    def next_id(self, prefix: str = "obs") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter:03d}"

    def build(self, debug: dict | None = None) -> ObservationGraph:
        return ObservationGraph(
            photo_id=self._photo_id,
            image_width=self._image_width,
            image_height=self._image_height,
            observations=list(self._observations),
            debug=debug or {},
        )

    @staticmethod
    def opening_semantics(element_type: str, confidence: float) -> dict[str, float]:
        if element_type == "window":
            return {
                "window": confidence,
                "door": max(0.0, 1.0 - confidence) * 0.2,
                "unknown_opening": max(0.0, 1.0 - confidence) * 0.15,
            }
        if element_type == "door":
            return {
                "door": confidence,
                "window": max(0.0, 1.0 - confidence) * 0.15,
                "unknown_opening": max(0.0, 1.0 - confidence) * 0.15,
            }
        return {
            "unknown_opening": confidence,
            "window": 0.1,
            "door": 0.1,
        }

    @staticmethod
    def make_facade_observation(
        obs_id: str,
        bbox_norm: list[float],
        confidence: float,
        source_type: str,
        metadata: dict | None = None,
    ) -> Observation:
        return Observation(
            id=obs_id,
            kind=ObservationKind.FACADE_CANDIDATE,
            geometry={"bbox": bbox_norm},
            semantic_candidates={"facade": confidence},
            confidence=confidence,
            sources=[
                ObservationSource(
                    type=source_type,
                    confidence=confidence,
                    metadata=metadata or {},
                )
            ],
        )

    @staticmethod
    def make_opening_observation(
        obs_id: str,
        bbox_norm: list[float],
        element_type: str,
        confidence: float,
        source_type: str,
        metadata: dict | None = None,
    ) -> Observation:
        semantics = ObservationGraphBuilder.opening_semantics(element_type, confidence)
        return Observation(
            id=obs_id,
            kind=ObservationKind.OPENING_CANDIDATE,
            geometry={"bbox": bbox_norm},
            semantic_candidates=semantics,
            confidence=confidence,
            sources=[
                ObservationSource(
                    type=source_type,
                    confidence=confidence,
                    metadata=metadata or {},
                )
            ],
        )
