from __future__ import annotations

import numpy as np

from geomora_rectify.facade_quad import estimate_facade_quad_from_lines
from geomora_rectify.line_detection import LineSegment


def test_line_quad_from_synthetic_facade():
    width, height = 1000, 800
    horizontal = [
        LineSegment(120, 120, 880, 130, 760.0, 0.01),
        LineSegment(100, 680, 900, 690, 800.0, 0.01),
    ]
    vertical = [
        LineSegment(140, 100, 150, 700, 600.0, 1.5),
        LineSegment(860, 100, 870, 700, 600.0, 1.5),
    ]

    quad = estimate_facade_quad_from_lines(width, height, horizontal, vertical, expand_ratio=0.0)
    assert quad is not None
    area_ratio = (
        0.5
        * abs(
            np.dot([p[0] for p in quad], np.roll([p[1] for p in quad], 1))
            - np.dot([p[1] for p in quad], np.roll([p[0] for p in quad], 1))
        )
        / float(width * height)
    )
    assert area_ratio > 0.4
