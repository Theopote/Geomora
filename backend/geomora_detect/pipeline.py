from __future__ import annotations

from pathlib import Path

import cv2

from .contour_detector import detect_contour_elements
from .facade_row_detector import detect_facade_row_elements
from .models import DetectionResult
from .scale_estimator import estimate_scale
from .yolo_detector import detect_yolo_elements, model_available

SUPPORTED_METHODS = ("auto", "contour_v1", "facade_row_v1", "yolo_v1")


def _with_scale_hint(result: DetectionResult) -> DetectionResult:
    hint = estimate_scale(result.elements, result.image_width, result.image_height)
    if hint:
        result.scale_hint = hint
        result.debug = {**result.debug, "scale_hint": hint}
    return result


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
        return _with_scale_hint(detect_contour_elements(image, return_overlay=return_overlay))

    if normalized_method == "facade_row_v1":
        return _with_scale_hint(detect_facade_row_elements(image, return_overlay=return_overlay))

    if normalized_method == "yolo_v1":
        return _with_scale_hint(detect_yolo_elements(image, return_overlay=return_overlay))

    if normalized_method == "auto":
        if model_available():
            yolo_result = detect_yolo_elements(image, return_overlay=return_overlay)
            if yolo_result.elements:
                return _with_scale_hint(yolo_result)
        row_result = detect_facade_row_elements(image, return_overlay=return_overlay)
        if row_result.elements:
            return _with_scale_hint(row_result)
        return _with_scale_hint(detect_contour_elements(image, return_overlay=return_overlay))
