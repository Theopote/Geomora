from __future__ import annotations

import cv2
import numpy as np
import pytest

from geomora_detect.pipeline import detect_facade
from geomora_detect.yolo_detector import model_available


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


def test_detect_facade_finds_windows_and_door(tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    result = detect_facade(str(path), method="contour_v1")

    assert result.method == "contour_v1"
    assert result.image_width == 800
    assert result.image_height == 600
    assert result.confidence > 0.4
    assert len(result.elements) >= 4

    windows = [element for element in result.elements if element.type == "window"]
    doors = [element for element in result.elements if element.type == "door"]
    assert len(windows) >= 4
    assert len(doors) >= 1
    assert result.overlay_base64


def test_detect_facade_rejects_missing_file(tmp_path):
    missing = tmp_path / "missing.jpg"
    with pytest.raises(ValueError, match="not found"):
        detect_facade(str(missing))


def test_detect_facade_rejects_invalid_method(tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    with pytest.raises(ValueError, match="Unsupported detection method"):
        detect_facade(str(path), method="sam_v1")


@pytest.mark.skipif(not model_available(), reason="YOLO ONNX model not built")
def test_detect_facade_yolo_on_synthetic(tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    result = detect_facade(str(path), method="yolo_v1")
    assert result.method == "yolo_v1"
    assert len(result.elements) >= 3
    assert result.overlay_base64


@pytest.mark.skipif(not model_available(), reason="YOLO ONNX model not built")
def test_detect_facade_auto_prefers_yolo(tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    result = detect_facade(str(path), method="auto")
    assert result.method == "yolo_v1"
