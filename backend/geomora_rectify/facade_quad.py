from __future__ import annotations

import numpy as np

from .line_detection import LineSegment
from .vanishing_point import intersect_lines


def _line_avg_x(line: LineSegment) -> float:
    return (line.x1 + line.x2) / 2.0


def _line_avg_y(line: LineSegment) -> float:
    return (line.y1 + line.y2) / 2.0


def _clamp_point(x: float, y: float, width: int, height: int) -> tuple[float, float]:
    return (
        float(np.clip(x, 0.0, width - 1.0)),
        float(np.clip(y, 0.0, height - 1.0)),
    )


def _expand_quad(
    corners: list[list[float]],
    width: int,
    height: int,
    expand_ratio: float,
) -> list[list[float]]:
    center_x = sum(point[0] for point in corners) / 4.0
    center_y = sum(point[1] for point in corners) / 4.0
    expanded: list[list[float]] = []

    for x, y in corners:
        dx = x - center_x
        dy = y - center_y
        expanded_x = center_x + dx * (1.0 + expand_ratio)
        expanded_y = center_y + dy * (1.0 + expand_ratio)
        clamped_x, clamped_y = _clamp_point(expanded_x, expanded_y, width, height)
        expanded.append([clamped_x, clamped_y])

    return expanded


def _quad_area(corners: list[list[float]]) -> float:
    points = np.array(corners, dtype=np.float64)
    x = points[:, 0]
    y = points[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def estimate_full_image_quad(width: int, height: int, margin_ratio: float = 0.02) -> list[list[float]]:
    margin_x = width * margin_ratio
    margin_y = height * margin_ratio
    left = margin_x
    right = width - margin_x
    top = margin_y
    bottom = height - margin_y
  # TL, TR, BR, BL
    return [
        [left, top],
        [right, top],
        [right, bottom],
        [left, bottom],
    ]


def estimate_facade_quad_from_lines(
    width: int,
    height: int,
    horizontal_lines: list[LineSegment],
    vertical_lines: list[LineSegment],
    expand_ratio: float = 0.06,
) -> list[list[float]] | None:
    """Build a perspective facade quad from horizontal / vertical line families.

    Returns corners in TL, TR, BR, BL order (image coordinates, y-down).
    """
    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        return None

    top_line = min(horizontal_lines, key=_line_avg_y)
    bottom_line = max(horizontal_lines, key=_line_avg_y)
    left_line = min(vertical_lines, key=_line_avg_x)
    right_line = max(vertical_lines, key=_line_avg_x)

    top_left = intersect_lines(left_line, top_line)
    top_right = intersect_lines(right_line, top_line)
    bottom_right = intersect_lines(right_line, bottom_line)
    bottom_left = intersect_lines(left_line, bottom_line)
    if any(point is None for point in (top_left, top_right, bottom_right, bottom_left)):
        return None

    quad = [
        list(top_left),
        list(top_right),
        list(bottom_right),
        list(bottom_left),
    ]

    area_ratio = _quad_area(quad) / float(width * height)
    if area_ratio < 0.08 or area_ratio > 0.98:
        return None

    widths = [
        abs(quad[1][0] - quad[0][0]),
        abs(quad[2][0] - quad[3][0]),
    ]
    heights = [
        abs(quad[3][1] - quad[0][1]),
        abs(quad[2][1] - quad[1][1]),
    ]
    if min(widths) < width * 0.15 or min(heights) < height * 0.15:
        return None

    return _expand_quad(quad, width, height, expand_ratio)


def estimate_facade_quad(
    width: int,
    height: int,
    horizontal_lines: list[LineSegment],
    vertical_lines: list[LineSegment],
    vanishing_points: list[tuple[float, float] | None],
) -> tuple[list[list[float]], str]:
    _ = vanishing_points
    line_quad = estimate_facade_quad_from_lines(width, height, horizontal_lines, vertical_lines)
    if line_quad is not None:
        return line_quad, "auto_line_intersections"

    return estimate_full_image_quad(width, height, margin_ratio=0.02), "auto_full_frame"
