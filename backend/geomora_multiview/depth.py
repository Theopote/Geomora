from __future__ import annotations

import cv2
import numpy as np

from .colmap_depth import load_colmap_depth_map
from .depth_registry import available_models, resolve_auto_neural_method
from .neural_depth import DepthModelNotFoundError, model_available, relative_depth_map_neural

DEPTH_METHODS = (
    "auto",
    "gradient_laplacian_v1",
    "colmap_dense_v1",
    "depth_anything_v2_small_v1",
    "depth_anything_v2_small_q4_v1",
    "marigold_v1_1_v1",
    "midas_v21_v1",
)

NEURAL_METHODS = {
    "depth_anything_v2_small_v1",
    "depth_anything_v2_small_q4_v1",
    "marigold_v1_1_v1",
    "midas_v21_v1",
}


def resolve_depth_method(method: str) -> str:
    normalized = (method or "auto").strip().lower()
    if normalized == "auto":
        return resolve_auto_neural_method() or "gradient_laplacian_v1"
    if normalized not in DEPTH_METHODS:
        raise ValueError(f"Unsupported depth method: {method}")
    if normalized in NEURAL_METHODS and not model_available(normalized):
        raise ValueError(_missing_model_message(normalized))
    return normalized


def _missing_model_message(method: str) -> str:
    if method == "depth_anything_v2_small_v1":
        return "Depth Anything V2 model not found. Run backend/scripts/download_depth_models.py --model da2"
    if method == "depth_anything_v2_small_q4_v1":
        return "Depth Anything V2 Q4 model not found. Run backend/scripts/download_depth_models.py --model da2-q4"
    if method == "marigold_v1_1_v1":
        return "Marigold backend unavailable. Install: pip install -r backend/requirements-depth.txt"
    if method == "midas_v21_v1":
        return "MiDaS depth model not found. Run backend/scripts/download_depth_models.py --model midas"
    if method == "colmap_dense_v1":
        return "COLMAP dense depth unavailable. Use register_method=colmap_dense_v1 during fusion."
    return f"Depth model unavailable: {method}"


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


def compute_depth_map(
    image_bgr: np.ndarray,
    method: str = "auto",
    *,
    colmap_depth_path: str | None = None,
) -> tuple[np.ndarray, str]:
    normalized = (method or "auto").strip().lower()

    if normalized in {"auto", "colmap_dense_v1"} and colmap_depth_path:
        try:
            return load_colmap_depth_map(colmap_depth_path), "colmap_dense_v1"
        except FileNotFoundError as error:
            if normalized == "colmap_dense_v1":
                raise ValueError(str(error)) from error

    if normalized == "colmap_dense_v1":
        raise ValueError(_missing_model_message("colmap_dense_v1"))

    resolved = resolve_depth_method(method)
    if resolved in NEURAL_METHODS:
        try:
            return relative_depth_map_neural(resolved, image_bgr), resolved
        except (DepthModelNotFoundError, RuntimeError) as error:
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


def depth_capabilities() -> dict[str, object]:
    from .onnx_providers import onnx_device_info

    models = available_models()
    return {
        "depth_models": models,
        "depth_auto": resolve_auto_neural_method() or "gradient_laplacian_v1",
        "depth_methods": list(DEPTH_METHODS),
        "onnx_device": onnx_device_info(),
    }
