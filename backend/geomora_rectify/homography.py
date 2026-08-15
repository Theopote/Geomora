from __future__ import annotations

import math

import cv2
import numpy as np

from .facade_quad import estimate_full_image_quad


def order_points_clockwise(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype=np.float32)
    s = points.sum(axis=1)
    ordered[0] = points[np.argmin(s)]
    ordered[2] = points[np.argmax(s)]
    diff = np.diff(points, axis=1)
    ordered[1] = points[np.argmin(diff)]
    ordered[3] = points[np.argmax(diff)]
    return ordered


def destination_size(corners: np.ndarray) -> tuple[int, int]:
    # corners: TL, TR, BR, BL
    top_width = np.linalg.norm(corners[1] - corners[0])
    bottom_width = np.linalg.norm(corners[2] - corners[3])
    left_height = np.linalg.norm(corners[3] - corners[0])
    right_height = np.linalg.norm(corners[2] - corners[1])
    max_width = int(max(top_width, bottom_width))
    max_height = int(max(left_height, right_height))
    return max(max_width, 1), max(max_height, 1)


def compute_rectifying_homography(
    corners_src: list[list[float]],
    output_size: tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    if len(corners_src) != 4:
        raise ValueError("Exactly four source corners are required")

    # Input order: TL, TR, BR, BL (image coordinates, y-down).
    src = np.array(corners_src, dtype=np.float32)
    if output_size is None:
        width, height = destination_size(src)
    else:
        width, height = output_size

    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    homography = cv2.getPerspectiveTransform(src, dst)
    return homography, dst, (width, height)


def warp_image(image: np.ndarray, homography: np.ndarray, output_size: tuple[int, int]) -> np.ndarray:
    width, height = output_size
    return cv2.warpPerspective(image, homography, (width, height))


def estimate_facade_quad_from_vps(
    width: int,
    height: int,
    vanishing_points: list[tuple[float, float] | None],
    margin_ratio: float = 0.03,
) -> list[list[float]]:
    """Legacy helper — full-frame inset quad (TL, TR, BR, BL)."""
    _ = vanishing_points
    return estimate_full_image_quad(width, height, margin_ratio=margin_ratio)


def quad_confidence(
    corners: list[list[float]],
    width: int,
    height: int,
    line_count: int,
    vanishing_points: list[tuple[float, float] | None],
    manual: bool,
) -> float:
    if manual:
        return 1.0

    area = polygon_area(np.array(corners, dtype=np.float32))
    image_area = float(width * height)
    area_ratio = area / image_area if image_area else 0.0

    score = 0.35
    if line_count >= 12:
        score += 0.2
    if line_count >= 24:
        score += 0.1

    finite_vps = [vp for vp in vanishing_points if vp is not None]
    if len(finite_vps) >= 1:
        score += 0.15
    if len(finite_vps) >= 2:
        score += 0.15

    if 0.2 <= area_ratio <= 0.85:
        score += 0.1

    return round(min(score, 0.95), 2)


def polygon_area(points: np.ndarray) -> float:
    x = points[:, 0]
    y = points[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))
