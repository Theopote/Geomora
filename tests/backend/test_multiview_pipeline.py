from __future__ import annotations

import cv2
import numpy as np
import pytest

from geomora_multiview.pipeline import register_views


def _facade_with_offset(width: int = 800, height: int = 600, shift_x: int = 0, shift_y: int = 0) -> np.ndarray:
    image = np.full((height, width, 3), (210, 205, 198), dtype=np.uint8)
    cv2.rectangle(image, (80 + shift_x, 60 + shift_y), (width - 60 + shift_x, height - 50 + shift_y), (175, 168, 158), -1)
    for x1, y1, x2, y2 in [
        (120 + shift_x, 140 + shift_y, 220 + shift_x, 320 + shift_y),
        (280 + shift_x, 140 + shift_y, 380 + shift_x, 320 + shift_y),
        (440 + shift_x, 140 + shift_y, 540 + shift_x, 320 + shift_y),
    ]:
        cv2.rectangle(image, (x1, y1), (x2, y2), (120, 175, 220), -1)
    cv2.rectangle(image, (200 + shift_x, 350 + shift_y, 320 + shift_x, 520 + shift_y), (90, 140, 95), -1)
    return image


def test_register_views_finds_homography(tmp_path):
    primary = tmp_path / "primary.jpg"
    secondary = tmp_path / "secondary.jpg"
    primary_image = _facade_with_offset()
    transform = np.float32([[1, 0, 18], [0, 1, 12]])
    secondary_image = cv2.warpAffine(primary_image, transform, (primary_image.shape[1], primary_image.shape[0]))
    cv2.imwrite(str(primary), primary_image)
    cv2.imwrite(str(secondary), secondary_image)

    result = register_views(str(primary), str(secondary))

    assert result.method == "feature_homography_v1"
    assert result.match_count >= 8
    assert result.inlier_count >= 4
    assert result.confidence > 0.3
    assert result.homography is not None
    assert len(result.views) == 2
    assert result.views[0].role == "primary"
    assert result.views[1].role == "secondary"
    assert result.views[1].transform_to_primary is not None


def test_register_views_rejects_missing_file(tmp_path):
    primary = tmp_path / "primary.jpg"
    missing = tmp_path / "missing.jpg"
    cv2.imwrite(str(primary), _facade_with_offset())

    with pytest.raises(ValueError, match="not found"):
        register_views(str(primary), str(missing))
