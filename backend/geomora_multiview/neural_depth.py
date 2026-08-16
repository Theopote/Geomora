from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from .depth_preprocess import dpt_v2, imagenet_square, resize_depth_to_image
from .depth_registry import (
    DepthModelNotFoundError,
    load_registry,
    marigold_model_available,
    model_available,
    onnx_model_available,
    resolve_auto_neural_method,
    resolve_model_paths,
)
from .onnx_providers import active_onnx_provider, resolve_onnx_providers


@lru_cache(maxsize=8)
def _load_session(model_path: str, provider_key: str):
    import onnxruntime as ort

    return ort.InferenceSession(
        model_path,
        providers=resolve_onnx_providers(),
    )


def _resolve_io_names(session, config: dict) -> tuple[str, str]:
    input_name = config.get("input_name") or session.get_inputs()[0].name
    output_name = config.get("output_name") or session.get_outputs()[0].name
    return input_name, output_name


def relative_depth_map_onnx(model_id: str, image_bgr: np.ndarray) -> np.ndarray:
    registry = load_registry()
    if model_id not in registry:
        raise DepthModelNotFoundError(f"Unknown depth model: {model_id}")

    config = registry[model_id]
    model_path, _data_path = resolve_model_paths(model_id)
    provider_key = active_onnx_provider()
    session = _load_session(str(model_path), provider_key)
    input_name, output_name = _resolve_io_names(session, config)

    preprocess = config.get("preprocess", "imagenet_square")
    model_size: tuple[int, int] | None = None
    if preprocess == "dpt_v2":
        tensor, model_size = dpt_v2(
            image_bgr,
            int(config.get("input_size", 518)),
            int(config.get("ensure_multiple_of", 14)),
            config.get("mean", [0.485, 0.456, 0.406]),
            config.get("std", [0.229, 0.224, 0.225]),
        )
    else:
        tensor = imagenet_square(
            image_bgr,
            int(config.get("input_size", 256)),
            config.get("mean", [0.485, 0.456, 0.406]),
            config.get("std", [0.229, 0.224, 0.225]),
        )

    output = session.run([output_name], {input_name: tensor})[0]
    depth = output.squeeze().astype(np.float32)
    return resize_depth_to_image(depth, image_bgr, model_size)


def relative_depth_map_midas(image_bgr: np.ndarray) -> np.ndarray:
    return relative_depth_map_onnx("midas_v21_v1", image_bgr)


def relative_depth_map_depth_anything_v2(image_bgr: np.ndarray) -> np.ndarray:
    return relative_depth_map_onnx("depth_anything_v2_small_v1", image_bgr)


def relative_depth_map_neural(model_id: str, image_bgr: np.ndarray) -> np.ndarray:
    if model_id == "marigold_v1_1_v1":
        from .marigold_depth import relative_depth_map_marigold

        return relative_depth_map_marigold(image_bgr)
    return relative_depth_map_onnx(model_id, image_bgr)


__all__ = [
    "DepthModelNotFoundError",
    "marigold_model_available",
    "model_available",
    "onnx_model_available",
    "resolve_auto_neural_method",
    "relative_depth_map_depth_anything_v2",
    "relative_depth_map_midas",
    "relative_depth_map_neural",
]
