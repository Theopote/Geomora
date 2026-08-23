from __future__ import annotations

import os


def configure_onnx_device(device: str) -> str:
    normalized = (device or "auto").strip().lower()
    if normalized == "directml":
        normalized = "dml"
    if normalized not in {"auto", "cpu", "cuda", "dml"}:
        raise ValueError("ONNX device must be auto, cpu, cuda or directml")
    os.environ["GEOMORA_ONNX_DEVICE"] = normalized
    return normalized


def _available_providers() -> list[str]:
    try:
        import onnxruntime as ort

        return list(ort.get_available_providers())
    except Exception:  # pragma: no cover - optional import guard
        return ["CPUExecutionProvider"]


def resolve_onnx_providers() -> list[str]:
    device = (os.environ.get("GEOMORA_ONNX_DEVICE") or "auto").strip().lower()
    available = _available_providers()

    if device == "cpu":
        return ["CPUExecutionProvider"]

    if device == "cuda":
        if "CUDAExecutionProvider" in available:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    if device in {"dml", "directml"}:
        if "DmlExecutionProvider" in available:
            return ["DmlExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    for provider in ("CUDAExecutionProvider", "DmlExecutionProvider", "TensorrtExecutionProvider"):
        if provider in available:
            return [provider, "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def active_onnx_provider() -> str:
    return resolve_onnx_providers()[0]


def gpu_available() -> bool:
    return active_onnx_provider() != "CPUExecutionProvider"


def onnx_device_info() -> dict[str, object]:
    available = _available_providers()
    active = active_onnx_provider()
    return {
        "device_mode": (os.environ.get("GEOMORA_ONNX_DEVICE") or "auto").strip().lower(),
        "active_provider": active,
        "gpu_available": active != "CPUExecutionProvider",
        "available_providers": available,
    }
