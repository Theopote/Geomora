from __future__ import annotations

import numpy as np
import cv2

from geomora_rectify.homography import compute_rectifying_homography, warp_image
from geomora_rectify.line_detection import detect_lines
from geomora_rectify.pipeline import rectify_image


def _synthetic_perspective_image(width: int = 640, height: int = 480) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (220, 220, 220)

    pts = np.array([[80, 420], [560, 380], [520, 80], [120, 120]], dtype=np.float32)
    cv2.fillConvexPoly(image, pts.astype(np.int32), (180, 180, 200))
    for x in range(140, 500, 80):
        cv2.rectangle(image, (x, 180), (x + 40, 320), (40, 40, 160), 2)
    return image


def test_detect_lines_on_synthetic_image(tmp_path):
    image = _synthetic_perspective_image()
    path = tmp_path / "synthetic.jpg"
    cv2.imwrite(str(path), image)

    lines = detect_lines(image)
    assert len(lines) >= 4


def test_manual_corner_rectification(tmp_path):
    image = _synthetic_perspective_image()
    path = tmp_path / "synthetic.jpg"
    output = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    corners = [[80, 420], [560, 380], [520, 80], [120, 120]]
    result = rectify_image(str(path), output_path=str(output), corners=corners)

    assert result.confidence == 1.0
    assert result.method == "manual_corners"
    assert output.exists()
    assert result.output_width > 0
    assert result.output_height > 0
    assert len(result.homography) == 3


def test_auto_rectification_pipeline(tmp_path):
    image = _synthetic_perspective_image()
    path = tmp_path / "synthetic.jpg"
    output = tmp_path / "rectified.jpg"
    cv2.imwrite(str(path), image)

    result = rectify_image(str(path), output_path=str(output))
    assert result.method == "auto_vanishing_point"
    assert output.exists()
    assert 0.0 < result.confidence <= 1.0


def test_compute_homography_dimensions():
    corners = [[0, 0], [200, 20], [180, 300], [0, 280]]
    homography, _, size = compute_rectifying_homography(corners)
    rectified = warp_image(np.zeros((400, 400, 3), dtype=np.uint8), homography, size)
    assert rectified.shape[1] == size[0]
    assert rectified.shape[0] == size[1]
