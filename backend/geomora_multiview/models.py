from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ViewRegistration:
    id: str
    role: str
    image_width: int
    image_height: int
    transform_to_primary: list[list[float]] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "image_width": self.image_width,
            "image_height": self.image_height,
        }
        if self.transform_to_primary is not None:
            payload["transform_to_primary"] = self.transform_to_primary
        return payload


@dataclass
class MultiviewResult:
    method: str
    confidence: float
    match_count: int
    inlier_count: int
    views: list[ViewRegistration] = field(default_factory=list)
    homography: list[list[float]] | None = None
    debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "confidence": round(self.confidence, 4),
            "match_count": self.match_count,
            "inlier_count": self.inlier_count,
            "homography": self.homography,
            "views": [view.to_dict() for view in self.views],
            "debug": self.debug,
        }
