from __future__ import annotations

from geomora_rectify.homography import estimate_facade_quad_from_vps, polygon_area
import numpy as np


def test_auto_quad_keeps_most_of_image():
    width, height = 1200, 800
    quad = estimate_facade_quad_from_vps(width, height, [None, None])
    area_ratio = polygon_area(np.array(quad, dtype=np.float32)) / float(width * height)
    assert area_ratio >= 0.88
