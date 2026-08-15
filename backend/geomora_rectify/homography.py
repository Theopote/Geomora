from __future__ import annotations

import math

import cv2
import numpy as np


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
    ordered = order_points_clockwise(corners)
    width_a = np.linalg.norm(ordered[2] - ordered[3])
    width_b = np.linalg.norm(ordered[1] - ordered[0])
    height_a = np.linalg.norm(ordered[1] - ordered[2])
    height_b = np.linalg.norm(ordered[0] - ordered[3])
    max_width = int(max(width_a, width_b))
    max_height = int(max(height_a, height_b))
    return max(max_width, 1), max(max_height, 1)


def compute_rectifying_homography(
    corners_src: list[list[float]],
    output_size: tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    if len(corners_src) != 4:
        raise ValueError("Exactly four source corners are required")

    src = order_points_clockwise(np.array(corners_src, dtype=np.float32))
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
    """Estimate facade region from image bounds with a small inset.

    Auto mode keeps most of the photo visible. Aggressive VP-based cropping
    removed in v0.4.1 — it often cut off rooflines and ground. Use manual
    corners when the building does not fill the frame.
    """
    _ = vanishing_points  # reserved for future perspective-aware quads
    margin_x = width * margin_ratio
    margin_y = height * margin_ratio

    left = margin_x
    right = width - margin_x
    top = margin_y
    bottom = height - margin_y

    return [
        [left, bottom],
        [right, bottom],
        [right, top],
        [left, top],
    ]


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
