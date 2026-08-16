from __future__ import annotations

import cv2
import numpy as np
import pytest

from geomora_detect.mask_refiner import (
    bbox_iou,
    refine_bbox,
    refine_elements,
    refine_detection_result,
)
from geomora_detect.models import DetectedElement, DetectionResult


def _synthetic_rectified(width: int = 800, height: int = 600) -> np.ndarray:
    image = np.full((height, width, 3), (210, 210, 210), dtype=np.uint8)
    cv2.rectangle(image, (20, 40), (width - 20, height - 40), (175, 168, 158), -1)
    for x1, y1, x2, y2 in (
        (80, 140, 200, 320),
        (240, 140, 360, 320),
        (400, 140, 520, 320),
        (560, 140, 680, 320),
    ):
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)
    cv2.rectangle(image, (10, 330), (70, 560), (25, 25, 90), -1)
    return image


def test_refine_bbox_stays_inside_prompt():
    image = _synthetic_rectified()
    prompt = [0.10, 0.23, 0.25, 0.53]
    refined, backend, _ = refine_bbox(image, prompt, element_type="window")
    assert backend in {"mobile_sam_v1", "grabcut_v1", "threshold_v1", "prompt_only"}
    assert bbox_iou(prompt, refined) >= 0.35


def test_refine_elements_keeps_counts():
    image = _synthetic_rectified()
    elements = [
        DetectedElement(type="window", bbox_norm=[0.10, 0.23, 0.25, 0.53], confidence=0.9),
        DetectedElement(type="door", bbox_norm=[0.01, 0.55, 0.09, 0.93], confidence=0.8),
    ]
    refined, masks, debug = refine_elements(image, elements)
    assert len(refined) == 2
    assert len(masks) == 2
    assert debug["element_count"] == 2


def test_refine_detection_result_sets_sam_method():
    image = _synthetic_rectified()
    base = DetectionResult(
        method="yolo_v1",
        confidence=0.8,
        image_width=800,
        image_height=600,
        elements=[
            DetectedElement(type="window", bbox_norm=[0.10, 0.23, 0.25, 0.53], confidence=0.9),
        ],
    )
    refined = refine_detection_result(image, base, return_overlay=True)
    assert refined.method == "sam_v1"
    assert refined.debug["base_method"] == "yolo_v1"
    assert refined.overlay_base64


def test_detect_facade_sam_v1(tmp_path):
    from geomora_detect.pipeline import detect_facade

    image = _synthetic_rectified()
    path = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    result = detect_facade(str(path), method="sam_v1")
    assert result.method == "sam_v1"
    assert len(result.elements) >= 3
    assert result.debug.get("refine_backend")
