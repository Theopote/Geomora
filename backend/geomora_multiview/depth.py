from __future__ import annotations

import cv2
import numpy as np


def relative_depth_map(gray: np.ndarray) -> np.ndarray:
    """Gradient-based relative depth proxy (higher = more salient / nearer contrast)."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    laplacian = cv2.Laplacian(blurred, cv2.CV_32F, ksize=3)
    magnitude = cv2.convertScaleAbs(laplacian).astype(np.float32)

    height, width = gray.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width]
    center_y = height / 2.0
    center_x = width / 2.0
    radial = np.sqrt((xx - center_x) ** 2 + (yy - center_y) ** 2)
    radial = radial / (radial.max() + 1e-6)

    depth = 0.65 * (magnitude / (magnitude.max() + 1e-6)) + 0.35 * (1.0 - radial)
    return np.clip(depth, 0.0, 1.0)


def opening_depth_score(depth_map: np.ndarray, bbox_norm: list[float]) -> float:
    height, width = depth_map.shape[:2]
    x1 = int(max(0, min(width - 1, bbox_norm[0] * width)))
    y1 = int(max(0, min(height - 1, bbox_norm[1] * height)))
    x2 = int(max(0, min(width, bbox_norm[2] * width)))
    y2 = int(max(0, min(height, bbox_norm[3] * height)))
    if x2 <= x1 or y2 <= y1:
        return 0.5

    region = depth_map[y1:y2, x1:x2]
    if region.size == 0:
        return 0.5
    return float(region.mean())
