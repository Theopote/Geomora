from __future__ import annotations

import base64

import cv2
import numpy as np

from .models import DetectedElement, DetectionResult


def _iou(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _suppress_overlaps(elements: list[DetectedElement], iou_threshold: float = 0.4) -> list[DetectedElement]:
    ordered = sorted(elements, key=lambda item: item.confidence, reverse=True)
    kept: list[DetectedElement] = []

    for candidate in ordered:
        if any(_iou(candidate.bbox_norm, existing.bbox_norm) > iou_threshold for existing in kept):
            continue
        kept.append(candidate)

    return sorted(kept, key=lambda item: item.bbox_norm[0])


def _classify_element(y_max: float, height_ratio: float, aspect: float) -> str:
    touches_floor = y_max > 0.78
    tall = height_ratio > 0.2
    narrow = aspect < 1.35
    if touches_floor and tall and narrow:
        return "door"
    return "window"


def _draw_overlay(image: np.ndarray, elements: list[DetectedElement]) -> np.ndarray:
    overlay = image.copy()
    colors = {
        "window": (66, 133, 244),
        "door": (52, 168, 83),
    }

    height, width = overlay.shape[:2]
    for element in elements:
        x1 = int(element.bbox_norm[0] * width)
        y1 = int(element.bbox_norm[1] * height)
        x2 = int(element.bbox_norm[2] * width)
        y2 = int(element.bbox_norm[3] * height)
        color = colors.get(element.type, (255, 200, 0))
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
        label = f"{element.type} {element.confidence:.2f}"
        cv2.putText(
            overlay,
            label,
            (x1, max(18, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    return overlay


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

    elements = _suppress_overlaps(candidates)
    doors = [element for element in elements if element.type == "door"]
    windows = [element for element in elements if element.type == "window"]

    if len(doors) > 1:
        best_door = max(doors, key=lambda item: item.confidence)
        elements = windows + [best_door]
    else:
        elements = windows + doors

    elements = sorted(elements, key=lambda item: (0 if item.type == "door" else 1, item.bbox_norm[0]))
    confidence = (
        sum(element.confidence for element in elements) / len(elements) if elements else 0.35
    )

    overlay_base64 = None
    if return_overlay:
        overlay = _draw_overlay(bgr, elements)
        ok, encoded = cv2.imencode(".jpg", overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if ok:
            overlay_base64 = base64.b64encode(encoded.tobytes()).decode("ascii")

    return DetectionResult(
        method="contour_v1",
        confidence=confidence,
        image_width=width,
        image_height=height,
        elements=elements,
        overlay_base64=overlay_base64,
        debug={"candidate_count": len(candidates), "element_count": len(elements)},
    )
