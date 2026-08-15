from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from .line_detection import LineSegment


def line_to_homogeneous(line: LineSegment) -> np.ndarray:
    p1 = np.array([line.x1, line.y1, 1.0])
    p2 = np.array([line.x2, line.y2, 1.0])
    return np.cross(p1, p2)


def intersect_lines(line_a: LineSegment, line_b: LineSegment) -> tuple[float, float] | None:
    la = line_to_homogeneous(line_a)
    lb = line_to_homogeneous(line_b)
    point = np.cross(la, lb)
    if abs(point[2]) < 1e-6:
        return None
    x = point[0] / point[2]
    y = point[1] / point[2]
    if not math.isfinite(x) or not math.isfinite(y):
        return None
    return float(x), float(y)


def estimate_vanishing_point(lines: Iterable[LineSegment], width: int, height: int) -> tuple[float, float] | None:
    samples: list[tuple[float, float]] = []
    line_list = list(lines)
    if len(line_list) < 2:
        return None

    for i in range(len(line_list)):
        for j in range(i + 1, len(line_list)):
            point = intersect_lines(line_list[i], line_list[j])
            if point is None:
                continue
            x, y = point
            margin = max(width, height) * 4
            if -margin <= x <= width + margin and -margin <= y <= height + margin:
                samples.append((x, y))

    if not samples:
        return None

    points = np.array(samples, dtype=np.float64)
    median = np.median(points, axis=0)
    return float(median[0]), float(median[1])


def estimate_vanishing_points(
    family_a: list[LineSegment],
    family_b: list[LineSegment],
    width: int,
    height: int,
) -> list[tuple[float, float] | None]:
    return [
        estimate_vanishing_point(family_a, width, height),
        estimate_vanishing_point(family_b, width, height),
    ]
