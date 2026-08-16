from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectedElement:
    type: str
    bbox_norm: list[float]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "bbox_norm": self.bbox_norm,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class DetectionResult:
    method: str
    confidence: float
    image_width: int
    image_height: int
    elements: list[DetectedElement] = field(default_factory=list)
    overlay_base64: str | None = None
    debug: dict[str, Any] = field(default_factory=dict)
    scale_hint: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "method": self.method,
            "confidence": round(self.confidence, 4),
            "image_width": self.image_width,
            "image_height": self.image_height,
            "elements": [element.to_dict() for element in self.elements],
            "overlay_base64": self.overlay_base64,
            "debug": self.debug,
        }
        if self.scale_hint:
            payload["scale_hint"] = self.scale_hint
        return payload
