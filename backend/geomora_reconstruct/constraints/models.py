from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConstraintPriority(str, Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class ConstraintSuggestion:
    id: str
    type: str
    targets: list[str]
    priority: ConstraintPriority
    confidence: float
    weight: float
    source: str
    evidence: dict[str, Any] = field(default_factory=dict)
    status: str = "proposed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "targets": self.targets,
            "priority": self.priority.value,
            "confidence": round(self.confidence, 4),
            "weight": round(self.weight, 4),
            "source": self.source,
            "evidence": self.evidence,
            "status": self.status,
        }
