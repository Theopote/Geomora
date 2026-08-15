from __future__ import annotations

import cv2
import numpy as np

from .models import DetectedElement, DetectionResult
from .nms import dedupe_doors, suppress_overlaps
from .overlays import draw_overlay, encode_overlay_jpeg


def _classify_element(y_max: float, height_ratio: float, aspect: float) -> str:
    touches_floor = y_max > 0.78
    tall = height_ratio > 0.2
    narrow = aspect < 1.35
    if touches_floor and tall and narrow:
        return "door"
    return "window"


def _collect_from_binary(
    binary: np.ndarray,
    width: int,
    height: int,
    min_area_ratio: float,
    max_area_ratio: float,
) -> list[DetectedElement]:
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = width * height * min_area_ratio
    max_area = width * height * max_area_ratio
    candidates: list[DetectedElement] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        x, y, box_width, box_height = cv2.boundingRect(contour)
        rect_area = box_width * box_height
        if rect_area <= 0:
            continue

        rectangularity = area / rect_area
        if rectangularity < 0.35:
            continue

        aspect = box_width / box_height if box_height > 0 else 0.0
        if aspect < 0.08 or aspect > 8.0:
            continue

        x_min = x / width
        y_min = y / height
        x_max = (x + box_width) / width
        y_max = (y + box_height) / height
        height_ratio = box_height / height
        element_type = _classify_element(y_max, height_ratio, aspect)
        confidence = min(0.95, 0.4 + rectangularity * 0.5)

        candidates.append(
            DetectedElement(
                type=element_type,
                bbox_norm=[x_min, y_min, x_max, y_max],
                confidence=confidence,
            )
        )

    return candidates


def _build_binary_masks(gray: np.ndarray) -> list[np.ndarray]:
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    masks: list[np.ndarray] = []

    _, otsu_inv = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    masks.append(otsu_inv)

    adaptive_inv = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        9,
    )
    masks.append(adaptive_inv)

    local_mean = cv2.GaussianBlur(blurred, (31, 31), 0)
    darker = (blurred.astype(np.float32) < local_mean.astype(np.float32) - 18.0).astype(np.uint8) * 255
    masks.append(darker)

    return masks


def _refine_binary(binary: np.ndarray) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    return cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)


def detect_contour_elements(image: np.ndarray, return_overlay: bool = True) -> DetectionResult:
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        bgr = image.copy()

    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    candidates: list[DetectedElement] = []
    for mask in _build_binary_masks(gray):
        refined = _refine_binary(mask)
        candidates.extend(
            _collect_from_binary(refined, width, height, min_area_ratio=0.0015, max_area_ratio=0.4)
        )

    elements = suppress_overlaps(candidates)
    elements = dedupe_doors(elements)
    confidence = (
        sum(element.confidence for element in elements) / len(elements) if elements else 0.35
    )

    overlay_base64 = None
    if return_overlay:
        overlay = draw_overlay(bgr, elements)
        overlay_base64 = encode_overlay_jpeg(overlay)

    return DetectionResult(
        method="contour_v1",
        confidence=confidence,
        image_width=width,
        image_height=height,
        elements=elements,
        overlay_base64=overlay_base64,
        debug={"candidate_count": len(candidates), "element_count": len(elements)},
    )
