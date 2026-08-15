from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "models" / "depth_config.json"


class MidasModelNotFoundError(FileNotFoundError):
    """Raised when the MiDaS ONNX model file is missing."""


@lru_cache(maxsize=1)
def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _load_session(model_path: str):
    import onnxruntime as ort

    return ort.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )


def load_depth_config(config_path: str | None = None) -> dict:
    path = Path(config_path or os.environ.get("GEOMORA_DEPTH_CONFIG", DEFAULT_CONFIG_PATH))
    if not path.exists():
        raise FileNotFoundError(f"Depth config not found: {path}")
    return _load_config(str(path))


def resolve_model_path(config: dict) -> Path:
    env_path = os.environ.get("GEOMORA_MIDAS_MODEL")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    model_file = config.get("model_file", "midas_v21_small.onnx")
    path = BACKEND_ROOT / "models" / model_file
    if path.exists():
        return path

    raise MidasModelNotFoundError(f"MiDaS model not found: {path}")


def model_available(config_path: str | None = None) -> bool:
    try:
        config = load_depth_config(config_path)
        resolve_model_path(config)
        return True
    except (MidasModelNotFoundError, FileNotFoundError, json.JSONDecodeError):
        return False


def _preprocess(image_bgr: np.ndarray, input_size: int, mean: list[float], std: list[float]) -> np.ndarray:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    resized = cv2.resize(rgb, (input_size, input_size), interpolation=cv2.INTER_CUBIC)
    normalized = (resized - np.array(mean, dtype=np.float32)) / np.array(std, dtype=np.float32)
    return np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]


def relative_depth_map_midas(image_bgr: np.ndarray, config_path: str | None = None) -> np.ndarray:
    config = load_depth_config(config_path)
    model_path = resolve_model_path(config)
    session = _load_session(str(model_path))

    input_size = int(config.get("input_size", 256))
    mean = config.get("mean", [0.485, 0.456, 0.406])
    std = config.get("std", [0.229, 0.224, 0.225])
    input_name = config.get("input_name", "input")
    output_name = config.get("output_name", "output")

    tensor = _preprocess(image_bgr, input_size, mean, std)
    output = session.run([output_name], {input_name: tensor})[0]
    depth = output.squeeze().astype(np.float32)

    height, width = image_bgr.shape[:2]
    depth = cv2.resize(depth, (width, height), interpolation=cv2.INTER_CUBIC)
    depth = depth - depth.min()
    depth = depth / (depth.max() + 1e-6)
    return np.clip(depth, 0.0, 1.0)
