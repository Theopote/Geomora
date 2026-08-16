from __future__ import annotations

import numpy as np
import pytest

from geomora_multiview.colmap_geometry import rasterize_depth_from_points
from geomora_multiview.colmap_model import ColmapCamera, ColmapImage, ColmapPoint3D
from geomora_multiview.colmap_depth import load_colmap_depth_map
from geomora_multiview.depth import compute_depth_map, resolve_depth_method
from geomora_multiview.depth_registry import auto_neural_priority
from geomora_multiview.onnx_providers import onnx_device_info, resolve_onnx_providers
from geomora_multiview.pipeline import REGISTER_METHODS, resolve_register_method


def test_resolve_onnx_providers_defaults_to_cpu():
    providers = resolve_onnx_providers()
    assert providers[0] == "CPUExecutionProvider"


def test_onnx_device_info_payload():
    payload = onnx_device_info()
    assert "active_provider" in payload
    assert "available_providers" in payload
    assert "gpu_available" in payload


def test_auto_neural_priority_prefers_q4_on_cpu(monkeypatch):
    monkeypatch.setattr("geomora_multiview.onnx_providers.gpu_available", lambda: False)
    assert auto_neural_priority()[0] == "depth_anything_v2_small_q4_v1"


def test_auto_neural_priority_prefers_full_da2_on_gpu(monkeypatch):
    monkeypatch.setattr("geomora_multiview.onnx_providers.gpu_available", lambda: True)
    assert auto_neural_priority()[0] == "depth_anything_v2_small_v1"


def test_resolve_depth_method_rejects_missing_q4():
    with pytest.raises(ValueError, match="Q4"):
        resolve_depth_method("depth_anything_v2_small_q4_v1")


def test_resolve_register_method_supports_colmap_dense(monkeypatch):
    monkeypatch.setattr("geomora_multiview.pipeline.colmap_available", lambda: True)
    assert resolve_register_method("colmap_dense_v1") == "colmap_dense_v1"
    assert "colmap_dense_v1" in REGISTER_METHODS


def test_rasterize_depth_from_colmap_points():
    camera = ColmapCamera(1, "PINHOLE", 200, 150, [180.0, 180.0, 100.0, 75.0])
    image = ColmapImage(1, (1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1, "primary.jpg", [])
    points = {
        1: ColmapPoint3D(1, (0.0, 0.0, 2.0), []),
        2: ColmapPoint3D(2, (0.2, 0.0, 3.0), []),
    }
    depth_map = rasterize_depth_from_points(points, image, camera, 150, 200)
    assert depth_map.shape == (150, 200)
    assert depth_map.max() <= 1.0
    assert depth_map.min() >= 0.0
    assert depth_map.sum() > 0.0


def test_load_colmap_depth_map_roundtrip(tmp_path):
    depth = np.array([[0.2, 0.8], [0.5, 0.1]], dtype=np.float32)
    path = tmp_path / "primary_depth.npy"
    np.save(path, depth)

    loaded = load_colmap_depth_map(path)
    assert loaded.shape == depth.shape
    assert loaded.max() <= 1.0


def test_compute_depth_map_uses_colmap_dense_when_available(tmp_path):
    depth = np.array([[0.0, 0.5], [1.0, 0.25]], dtype=np.float32)
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    path = tmp_path / "primary_depth.npy"
    np.save(path, depth)

    result, method = compute_depth_map(image, method="auto", colmap_depth_path=str(path))

    assert method == "colmap_dense_v1"
    assert result.shape == (2, 2)
