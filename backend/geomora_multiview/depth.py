from __future__ import annotations

import cv2
import numpy as np

from .neural_depth import MidasModelNotFoundError, model_available, relative_depth_map_midas

DEPTH_METHODS = ("auto", "gradient_laplacian_v1", "midas_v21_v1")


def resolve_depth_method(method: str) -> str:
    normalized = (method or "auto").strip().lower()
    if normalized == "auto":
        return "midas_v21_v1" if model_available() else "gradient_laplacian_v1"
    if normalized not in DEPTH_METHODS:
        raise ValueError(f"Unsupported depth method: {method}")
    if normalized == "midas_v21_v1" and not model_available():
        raise ValueError("MiDaS depth model not found. Run backend/scripts/download_midas_model.py")
    return normalized


def gradient_laplacian_v1(gray: np.ndarray) -> np.ndarray:
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


def compute_depth_map(image_bgr: np.ndarray, method: str = "auto") -> tuple[np.ndarray, str]:
    resolved = resolve_depth_method(method)
    if resolved == "midas_v21_v1":
        try:
            return relative_depth_map_midas(image_bgr), "midas_v21_v1"
        except MidasModelNotFoundError as error:
            if method == "auto":
                gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
                return gradient_laplacian_v1(gray), "gradient_laplacian_v1"
            raise ValueError(str(error)) from error

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return gradient_laplacian_v1(gray), "gradient_laplacian_v1"


def relative_depth_map(gray: np.ndarray) -> np.ndarray:
    """Backward-compatible gradient depth helper."""
    return gradient_laplacian_v1(gray)


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
