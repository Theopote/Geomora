from __future__ import annotations

import cv2
import numpy as np

from .contour_detector import _build_binary_masks, _classify_element, _refine_binary
from .models import DetectedElement, DetectionResult
from .nms import dedupe_doors, suppress_overlaps
from .overlays import draw_overlay, encode_overlay_jpeg


def _facade_bounds(edges: np.ndarray, width: int, height: int) -> tuple[int, int, int, int]:
    col_sum = edges.sum(axis=0).astype(np.float32)
    row_sum = edges.sum(axis=1).astype(np.float32)
    col_threshold = max(col_sum.max() * 0.12, 1.0)
    row_threshold = max(row_sum.max() * 0.10, 1.0)

    cols = np.where(col_sum >= col_threshold)[0]
    rows = np.where(row_sum >= row_threshold)[0]

    x1 = int(cols[0]) if cols.size else int(width * 0.04)
    x2 = int(cols[-1]) + 1 if cols.size else int(width * 0.96)
    y1 = int(rows[0]) if rows.size else int(height * 0.06)
    y2 = int(rows[-1]) + 1 if rows.size else int(height * 0.96)

    pad_x = int(width * 0.02)
    pad_y = int(height * 0.02)
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(width, x2 + pad_x)
    y2 = min(height, y2 + pad_y)

    if x2 - x1 < width * 0.35:
        x1, x2 = int(width * 0.04), int(width * 0.96)
    if y2 - y1 < height * 0.35:
        y1, y2 = int(height * 0.06), int(height * 0.96)

    return x1, y1, x2, y2


def _collect_roi_candidates(
    binary: np.ndarray,
    roi_width: int,
    roi_height: int,
    offset_x: int,
    offset_y: int,
    image_width: int,
    image_height: int,
) -> list[DetectedElement]:
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = roi_width * roi_height * 0.0012
    max_area = roi_width * roi_height * 0.35
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
        if rectangularity < 0.42:
            continue

        aspect = box_width / box_height if box_height > 0 else 0.0
        if aspect < 0.12 or aspect > 6.5:
            continue

        abs_x1 = offset_x + x
        abs_y1 = offset_y + y
        abs_x2 = abs_x1 + box_width
        abs_y2 = abs_y1 + box_height

        x_min = abs_x1 / image_width
        y_min = abs_y1 / image_height
        x_max = abs_x2 / image_width
        y_max = abs_y2 / image_height
        height_ratio = box_height / roi_height
        element_type = _classify_element(y_max, height_ratio, aspect)
        confidence = min(0.96, 0.45 + rectangularity * 0.45)

        candidates.append(
            DetectedElement(
                type=element_type,
                bbox_norm=[x_min, y_min, x_max, y_max],
                confidence=confidence,
            )
        )

    return candidates


def _filter_main_window_row(windows: list[DetectedElement]) -> list[DetectedElement]:
    if len(windows) <= 1:
        return windows

    centers = [((element.bbox_norm[1] + element.bbox_norm[3]) / 2.0) for element in windows]
    median_y = float(np.median(centers))
    tolerance = 0.09
    row = [
        element
        for element, center in zip(windows, centers, strict=True)
        if abs(center - median_y) <= tolerance
    ]
    return row if len(row) >= 2 else windows


def detect_facade_row_elements(image: np.ndarray, return_overlay: bool = True) -> DetectionResult:
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        bgr = image.copy()

    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 140)

    x1, y1, x2, y2 = _facade_bounds(edges, width, height)
    roi = gray[y1:y2, x1:x2]
    roi_height, roi_width = roi.shape[:2]

    candidates: list[DetectedElement] = []
    for mask in _build_binary_masks(roi):
        refined = _refine_binary(mask)
        candidates.extend(
            _collect_roi_candidates(refined, roi_width, roi_height, x1, y1, width, height)
        )

    elements = suppress_overlaps(candidates, iou_threshold=0.35)
    windows = [element for element in elements if element.type == "window"]
    doors = [element for element in elements if element.type == "door"]
    windows = _filter_main_window_row(windows)
    windows.sort(key=lambda element: element.bbox_norm[0])
    doors = sorted(doors, key=lambda element: -element.confidence)[:1]
    elements = windows + doors
    elements = dedupe_doors(elements)

    confidence = (
        sum(element.confidence for element in elements) / len(elements) if elements else 0.4
    )

    overlay_base64 = None
    if return_overlay:
        overlay = draw_overlay(bgr, elements)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 200, 255), 2)
        overlay_base64 = encode_overlay_jpeg(overlay)

    return DetectionResult(
        method="facade_row_v1",
        confidence=confidence,
        image_width=width,
        image_height=height,
        elements=elements,
        overlay_base64=overlay_base64,
        debug={
            "candidate_count": len(candidates),
            "element_count": len(elements),
            "facade_bounds": [x1, y1, x2, y2],
        },
    )
