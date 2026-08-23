from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ObservationKind(str, Enum):
    ARCHITECTURAL_EVIDENCE = "architectural_evidence"
    FACADE_CANDIDATE = "facade_candidate"
    OPENING_CANDIDATE = "opening_candidate"
    HORIZONTAL_LINE = "horizontal_line"
    DEPTH_DISCONTINUITY = "depth_discontinuity"
    BALCONY_CANDIDATE = "balcony_candidate"
    VERTICAL_LINE = "vertical_line"
    REPETITION_EVIDENCE = "repetition_evidence"
    OCCLUSION_REGION = "occlusion_region"
    METRIC_ANCHOR = "metric_anchor"


@dataclass
class ObservationSource:
    type: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {"type": self.type, "confidence": round(self.confidence, 4)}
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass
class SemanticCandidate:
    label: str
    probability: float

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "probability": round(self.probability, 4)}


@dataclass
class Observation:
    id: str
    kind: ObservationKind
    geometry: dict[str, Any]
    semantic_candidates: dict[str, float]
    confidence: float
    sources: list[ObservationSource] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "geometry": self.geometry,
            "semantic_candidates": {
                key: round(value, 4) for key, value in self.semantic_candidates.items()
            },
            "confidence": round(self.confidence, 4),
            "sources": [source.to_dict() for source in self.sources],
            "uncertainties": self.uncertainties,
        }


@dataclass
class ObservationGraph:
    schema_version: str = "observation-graph-v0.1"
    photo_id: str = ""
    image_width: int = 0
    image_height: int = 0
    observations: list[Observation] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "photo_id": self.photo_id,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "observations": [observation.to_dict() for observation in self.observations],
            "debug": self.debug,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ObservationGraph:
        observations = []
        for item in payload.get("observations", []):
            observations.append(
                Observation(
                    id=item["id"],
                    kind=ObservationKind(item["kind"]),
                    geometry=item.get("geometry", {}),
                    semantic_candidates=item.get("semantic_candidates", {}),
                    confidence=float(item.get("confidence", 0.0)),
                    sources=[
                        ObservationSource(
                            type=source["type"],
                            confidence=float(source["confidence"]),
                            metadata=source.get("metadata", {}),
                        )
                        for source in item.get("sources", [])
                    ],
                    uncertainties=list(item.get("uncertainties", [])),
                )
            )
        return cls(
            photo_id=payload.get("photo_id", ""),
            image_width=int(payload.get("image_width", 0)),
            image_height=int(payload.get("image_height", 0)),
            observations=observations,
            debug=dict(payload.get("debug", {})),
        )
