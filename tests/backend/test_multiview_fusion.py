from __future__ import annotations

import cv2
import numpy as np

from geomora_multiview.pipeline import fuse_openings


def _rectified_facade(width: int = 800, height: int = 600) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (210, 210, 210)
    for x1, y1, x2, y2 in [(80, 140, 200, 320), (240, 140, 360, 320), (400, 140, 520, 320)]:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)
    cv2.rectangle(image, (10, 330), (70, 560), (25, 25, 90), -1)
    return image


def test_fuse_openings_merges_two_views(tmp_path):
    primary = tmp_path / "primary.jpg"
    secondary = tmp_path / "secondary.jpg"
    primary_image = _rectified_facade()
    transform = np.float32([[1, 0, 12], [0, 1, 8]])
    secondary_image = cv2.warpAffine(primary_image, transform, (primary_image.shape[1], primary_image.shape[0]))
    cv2.imwrite(str(primary), primary_image)
    cv2.imwrite(str(secondary), secondary_image)

    result = fuse_openings(str(primary), str(secondary), detect_method="contour_v1")

    assert result.method == "multiview_fusion_v1"
    assert result.confidence > 0.3
    assert len(result.elements) >= 3
    assert result.homography is not None
    assert result.debug["primary_elements"] >= 3
    assert result.debug["fused_elements"] >= 3
