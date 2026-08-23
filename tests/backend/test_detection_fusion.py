from __future__ import annotations

import cv2
import numpy as np

from geomora_detect.detection_fusion import fuse_yolo_and_facade_row
from geomora_detect.facade_row_detector import detect_facade_row_elements
from geomora_detect.models import DetectedElement, DetectionResult
from geomora_detect.nms import filter_doors


def _empty_result(method: str, image: np.ndarray) -> DetectionResult:
    height, width = image.shape[:2]
    return DetectionResult(
        method=method,
        confidence=0.35,
        image_width=width,
        image_height=height,
        elements=[],
    )


def test_filter_doors_rejects_high_false_door_without_windows():
    false_door = DetectedElement(
        type="door",
        bbox_norm=[0.1, 0.2, 0.25, 0.45],
        confidence=0.48,
    )
    assert filter_doors([false_door], []) == []


def test_filter_doors_accepts_floor_level_door():
    door = DetectedElement(
        type="door",
        bbox_norm=[0.05, 0.55, 0.12, 0.92],
        confidence=0.75,
    )
    kept = filter_doors([door], [])
    assert len(kept) == 1
    assert kept[0].type == "door"


def test_fuse_adds_row_windows_when_yolo_misses():
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    image[:] = (210, 210, 210)
    for x1, y1, x2, y2 in [(80, 140, 200, 320), (240, 140, 360, 320), (400, 140, 520, 320)]:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)

    row_result = detect_facade_row_elements(image, return_overlay=False)
    false_door = DetectedElement(
        type="door",
        bbox_norm=[0.1, 0.2, 0.2, 0.4],
        confidence=0.4,
    )
    yolo_result = DetectionResult(
        method="yolo_v1",
        confidence=0.4,
        image_width=800,
        image_height=600,
        elements=[false_door],
    )

    fused = fuse_yolo_and_facade_row(yolo_result, row_result, image, return_overlay=False)
    windows = [element for element in fused.elements if element.type == "window"]
    doors = [element for element in fused.elements if element.type == "door"]

    assert fused.method == "auto_fusion_v1"
    assert len(windows) >= 3
    assert len(doors) == 0
