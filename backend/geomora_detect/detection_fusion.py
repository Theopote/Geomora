from __future__ import annotations

import cv2
import numpy as np

from .models import DetectedElement, DetectionResult
from .nms import dedupe_doors, filter_doors, iou, suppress_overlaps
from .overlays import draw_overlay, encode_overlay_jpeg


def fuse_yolo_and_facade_row(
    yolo_result: DetectionResult,
    row_result: DetectionResult,
    image: np.ndarray,
    *,
    return_overlay: bool = True,
    merge_iou_threshold: float = 0.35,
) -> DetectionResult:
    yolo_windows = [element for element in yolo_result.elements if element.type == "window"]
    row_windows = [element for element in row_result.elements if element.type == "window"]
    yolo_doors = [element for element in yolo_result.elements if element.type == "door"]
    row_doors = [element for element in row_result.elements if element.type == "door"]

    fused_windows = list(yolo_windows)
    for candidate in row_windows:
        overlaps = any(
            iou(candidate.bbox_norm, existing.bbox_norm) > merge_iou_threshold
            for existing in fused_windows
        )
        if not overlaps:
            fused_windows.append(candidate)

    if not fused_windows and row_windows:
        fused_windows = list(row_windows)

    fused_windows = suppress_overlaps(fused_windows, iou_threshold=merge_iou_threshold)
    fused_windows.sort(key=lambda element: element.bbox_norm[0])

    door_candidates = yolo_doors + row_doors
    fused_doors = filter_doors(door_candidates, fused_windows)
    elements = dedupe_doors(fused_windows + fused_doors)

    height, width = image.shape[:2]
    confidence = (
        sum(element.confidence for element in elements) / len(elements) if elements else 0.35
    )

    overlay_base64 = None
    if return_overlay:
        overlay = draw_overlay(image, elements)
        facade_bounds = row_result.debug.get("facade_bounds")
        if facade_bounds and len(facade_bounds) >= 4:
            x1, y1, x2, y2 = facade_bounds
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 200, 255), 2)
        overlay_base64 = encode_overlay_jpeg(overlay)

    facade_bounds = row_result.debug.get("facade_bounds")
    return DetectionResult(
        method="auto_fusion_v1",
        confidence=confidence,
        image_width=width,
        image_height=height,
        elements=elements,
        overlay_base64=overlay_base64,
        debug={
            "fusion": "yolo_facade_row_v1",
            "yolo_element_count": len(yolo_result.elements),
            "row_element_count": len(row_result.elements),
            "fused_element_count": len(elements),
            "yolo_window_count": len(yolo_windows),
            "row_window_count": len(row_windows),
            "fused_window_count": len(fused_windows),
            "facade_bounds": facade_bounds,
            "yolo_model_path": yolo_result.debug.get("model_path"),
        },
    )
