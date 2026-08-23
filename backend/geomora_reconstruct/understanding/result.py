from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StoreyBand:
    id: int
    y_min: float
    y_max: float
    confidence: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    status: str = "observed"

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "y_range": [round(self.y_min, 4), round(self.y_max, 4)],
            "confidence": round(self.confidence, 4),
            "status": self.status,
        }
        if self.evidence:
            payload["evidence"] = self.evidence
        return payload


@dataclass
class BayColumn:
    id: int
    x_center: float
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x_center": round(self.x_center, 4),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class UnderstandingResult:
    method: str = "understanding_v0.1"
    facade_bbox: list[float] | None = None
    storeys: list[StoreyBand] = field(default_factory=list)
    bays: list[BayColumn] = field(default_factory=list)
    pattern_groups: list[dict[str, Any]] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "facade_bbox": self.facade_bbox,
            "storeys": [storey.to_dict() for storey in self.storeys],
            "bays": [bay.to_dict() for bay in self.bays],
            "pattern_groups": self.pattern_groups,
            "uncertainties": self.uncertainties,
            "debug": self.debug,
        }
