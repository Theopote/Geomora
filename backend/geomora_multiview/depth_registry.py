from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_ROOT / "models"
REGISTRY_PATH = MODELS_DIR / "depth_models.json"
LEGACY_CONFIG_PATH = MODELS_DIR / "depth_config.json"

AUTO_NEURAL_PRIORITY_GPU = (
    "depth_anything_v2_small_v1",
    "depth_anything_v2_small_q4_v1",
    "marigold_v1_1_v1",
    "midas_v21_v1",
)
AUTO_NEURAL_PRIORITY_CPU = (
    "depth_anything_v2_small_q4_v1",
    "depth_anything_v2_small_v1",
    "marigold_v1_1_v1",
    "midas_v21_v1",
)


class DepthModelNotFoundError(FileNotFoundError):
    """Raised when a requested depth model file is missing."""


@lru_cache(maxsize=1)
def load_registry() -> dict[str, dict]:
    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open(encoding="utf-8") as handle:
            return json.load(handle)

    if LEGACY_CONFIG_PATH.exists():
        with LEGACY_CONFIG_PATH.open(encoding="utf-8") as handle:
            legacy = json.load(handle)
        return {
            "midas_v21_v1": {
                "label": "MiDaS v2.1 Small",
                "model_file": legacy.get("model_file", "midas_v21_small.onnx"),
                "preprocess": "imagenet_square",
                "input_size": legacy.get("input_size", 256),
                "mean": legacy.get("mean", [0.485, 0.456, 0.406]),
                "std": legacy.get("std", [0.229, 0.224, 0.225]),
                "input_name": legacy.get("input_name", "input"),
                "output_name": legacy.get("output_name", "output"),
                "env_var": "GEOMORA_MIDAS_MODEL",
            }
        }

    return {}


def resolve_model_paths(model_id: str) -> tuple[Path, Path | None]:
    registry = load_registry()
    if model_id not in registry:
        raise DepthModelNotFoundError(f"Unknown depth model: {model_id}")

    config = registry[model_id]
    env_var = config.get("env_var")
    if env_var:
        env_path = os.environ.get(env_var)
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path, None

    model_path = MODELS_DIR / config["model_file"]
    if not model_path.exists():
        raise DepthModelNotFoundError(f"Depth model not found: {model_path}")

    data_file = config.get("model_data_file")
    data_path = MODELS_DIR / data_file if data_file else None
    if data_path is not None and not data_path.exists():
        raise DepthModelNotFoundError(f"Depth model weights not found: {data_path}")

    return model_path, data_path


def onnx_model_available(model_id: str) -> bool:
    try:
        resolve_model_paths(model_id)
        return True
    except DepthModelNotFoundError:
        return False


def marigold_model_available() -> bool:
    try:
        from .marigold_depth import marigold_available

        return marigold_available()
    except Exception:  # pragma: no cover - optional import guard
        return False


def model_available(model_id: str) -> bool:
    if model_id == "marigold_v1_1_v1":
        return marigold_model_available()
    return onnx_model_available(model_id)


def auto_neural_priority() -> tuple[str, ...]:
    from .onnx_providers import gpu_available

    return AUTO_NEURAL_PRIORITY_GPU if gpu_available() else AUTO_NEURAL_PRIORITY_CPU


def resolve_auto_neural_method() -> str | None:
    for model_id in auto_neural_priority():
        if model_available(model_id):
            return model_id
    return None


def available_models() -> dict[str, bool]:
    registry = load_registry()
    payload = {model_id: onnx_model_available(model_id) for model_id in registry}
    payload["marigold_v1_1_v1"] = marigold_model_available()
    return payload
