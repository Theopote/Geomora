from __future__ import annotations

import math

import cv2
import numpy as np

from .models import LineSegment

MAX_IMAGE_DIM = 2048


def load_image(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return resize_if_needed(image)


def resize_if_needed(image: np.ndarray, max_dim: int = MAX_IMAGE_DIM) -> np.ndarray:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_dim:
        return image
    scale = max_dim / float(longest)
    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def detect_lines(image: np.ndarray, min_length: float = 40.0) -> list[LineSegment]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    lines: list[LineSegment] = []
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    detected, _, _, _ = lsd.detect(gray)

    if detected is not None:
        for entry in detected:
            coords = np.asarray(entry, dtype=np.float64).reshape(-1)
            if coords.size < 4:
                continue
            x1, y1, x2, y2 = coords[:4]
            segment = _make_segment(float(x1), float(y1), float(x2), float(y2))
            if segment.length >= min_length:
                lines.append(segment)

    if len(lines) < 8:
        hough = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=50,
            minLineLength=int(min_length),
            maxLineGap=16,
        )
        if hough is not None:
            for entry in hough:
                x1, y1, x2, y2 = entry[0]
                lines.append(_make_segment(float(x1), float(y1), float(x2), float(y2)))

    return _dedupe_lines(lines)


def classify_line_families(lines: list[LineSegment]) -> tuple[list[LineSegment], list[LineSegment]]:
    if not lines:
        return [], []

    angles = np.array([line.angle for line in lines], dtype=np.float64)
    angles = np.mod(angles, math.pi)

    # Split into two dominant orientation clusters.
    threshold = math.pi / 4.0
    group_a = [line for line in lines if line.angle < threshold or line.angle >= math.pi - threshold]
    group_b = [line for line in lines if line not in group_a]

    if len(group_a) < len(group_b):
        group_a, group_b = group_b, group_a

    return group_a, group_b


def _make_segment(x1: float, y1: float, x2: float, y2: float) -> LineSegment:
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    angle = math.atan2(abs(dy), abs(dx))
    return LineSegment(x1=x1, y1=y1, x2=x2, y2=y2, length=length, angle=angle)


def _dedupe_lines(lines: list[LineSegment], min_dist: float = 8.0) -> list[LineSegment]:
    unique: list[LineSegment] = []
    for line in sorted(lines, key=lambda item: item.length, reverse=True):
        duplicate = False
        for existing in unique:
            if (
                abs(line.x1 - existing.x1) < min_dist
                and abs(line.y1 - existing.y1) < min_dist
                and abs(line.x2 - existing.x2) < min_dist
                and abs(line.y2 - existing.y2) < min_dist
            ):
                duplicate = True
                break
        if not duplicate:
            unique.append(line)
    return unique
