from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineSegment:
    x1: float
    y1: float
    x2: float
    y2: float
    length: float
    angle: float


@dataclass
class RectificationResult:
    rectified_image_path: str | None = None
    rectified_image_base64: str | None = None
    homography: list[list[float]] = field(default_factory=list)
    vanishing_points: list[list[float | None]] = field(default_factory=list)
    corners_src: list[list[float]] = field(default_factory=list)
    corners_dst: list[list[float]] = field(default_factory=list)
    confidence: float = 0.0
    method: str = "unknown"
    line_count: int = 0
    output_width: int = 0
    output_height: int = 0
    debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rectified_image_path": self.rectified_image_path,
            "rectified_image_base64": self.rectified_image_base64,
            "homography": self.homography,
            "vanishing_points": self.vanishing_points,
            "corners_src": self.corners_src,
            "corners_dst": self.corners_dst,
            "confidence": self.confidence,
            "method": self.method,
            "line_count": self.line_count,
            "output_width": self.output_width,
            "output_height": self.output_height,
            "debug": self.debug,
        }
