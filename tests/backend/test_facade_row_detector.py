from __future__ import annotations

import cv2
import numpy as np
import pytest

from geomora_detect.facade_row_detector import detect_facade_row_elements
from geomora_detect.pipeline import detect_facade
from geomora_detect.scale_estimator import estimate_scale


def _synthetic_rectified_facade(width: int = 800, height: int = 600) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (210, 210, 210)

    windows = [
        (80, 140, 200, 320),
        (240, 140, 360, 320),
        (400, 140, 520, 320),
        (560, 140, 680, 320),
    ]
    for x1, y1, x2, y2 in windows:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)

    cv2.rectangle(image, (10, 330), (70, 560), (25, 25, 90), -1)
    return image


def test_facade_row_detector_finds_openings():
    image = _synthetic_rectified_facade()
    result = detect_facade_row_elements(image)

    assert result.method == "facade_row_v1"
    windows = [element for element in result.elements if element.type == "window"]
    doors = [element for element in result.elements if element.type == "door"]
    assert len(windows) >= 4
    assert len(doors) >= 1


def test_scale_estimator_from_door(tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    result = detect_facade(str(path), method="facade_row_v1")
    hint = estimate_scale(result.elements, result.image_width, result.image_height)

    assert hint is not None
    assert hint["wall_height_mm"] >= 2400
    assert hint["wall_length_mm"] >= 4000
    assert result.scale_hint is not None


def test_detect_facade_auto_includes_scale_hint(tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    result = detect_facade(str(path), method="facade_row_v1")
    payload = result.to_dict()

    assert payload.get("scale_hint")
    assert payload["scale_hint"]["wall_length_mm"] > 0
