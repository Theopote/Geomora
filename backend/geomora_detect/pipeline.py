from __future__ import annotations

from pathlib import Path

import cv2

from .contour_detector import detect_contour_elements
from .models import DetectionResult
from .yolo_detector import detect_yolo_elements, model_available

SUPPORTED_METHODS = ("auto", "contour_v1", "yolo_v1")


def detect_facade(
    image_path: str,
    *,
    method: str = "auto",
    return_overlay: bool = True,
) -> DetectionResult:
    normalized_method = (method or "auto").strip().lower()
    if normalized_method not in SUPPORTED_METHODS:
        raise ValueError(
            f"Unsupported detection method: {method}. "
            f"Use one of: {', '.join(SUPPORTED_METHODS)}"
        )

    path = Path(image_path)
    if not path.exists():
        raise ValueError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    if normalized_method == "contour_v1":
        return detect_contour_elements(image, return_overlay=return_overlay)

    if normalized_method == "yolo_v1":
        return detect_yolo_elements(image, return_overlay=return_overlay)

    if model_available():
        return detect_yolo_elements(image, return_overlay=return_overlay)

    return detect_contour_elements(image, return_overlay=return_overlay)
