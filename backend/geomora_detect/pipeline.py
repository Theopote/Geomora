from __future__ import annotations

from pathlib import Path

import cv2

from .contour_detector import detect_contour_elements
from .models import DetectionResult


def detect_facade(
    image_path: str,
    *,
    return_overlay: bool = True,
) -> DetectionResult:
    path = Path(image_path)
    if not path.exists():
        raise ValueError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    return detect_contour_elements(image, return_overlay=return_overlay)
