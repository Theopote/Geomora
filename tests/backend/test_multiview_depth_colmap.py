from __future__ import annotations

import numpy as np
import pytest

from geomora_multiview.colmap_model import read_images_text, read_points3d_text
from geomora_multiview.depth import compute_depth_map, depth_capabilities, resolve_depth_method
from geomora_multiview.depth_preprocess import dpt_v2
from geomora_multiview.depth_registry import resolve_auto_neural_method
from geomora_multiview.pipeline import fuse_openings, multiview_capabilities, resolve_register_method


def test_resolve_depth_method_defaults_to_gradient_without_model(monkeypatch):
    monkeypatch.setattr("geomora_multiview.depth.resolve_auto_neural_method", lambda: None)
    assert resolve_depth_method("auto") == "gradient_laplacian_v1"


def test_resolve_depth_method_prefers_depth_anything_when_available(monkeypatch):
    monkeypatch.setattr("geomora_multiview.depth.resolve_auto_neural_method", lambda: "depth_anything_v2_small_v1")
    assert resolve_depth_method("auto") == "depth_anything_v2_small_v1"


def test_resolve_depth_method_explicit_gradient():
    assert resolve_depth_method("gradient_laplacian_v1") == "gradient_laplacian_v1"


def test_resolve_depth_method_rejects_missing_midas():
    with pytest.raises(ValueError, match="MiDaS"):
        resolve_depth_method("midas_v21_v1")


def test_resolve_depth_method_rejects_missing_depth_anything():
    with pytest.raises(ValueError, match="Depth Anything"):
        resolve_depth_method("depth_anything_v2_small_v1")


def test_dpt_v2_preprocess_keeps_aspect_and_multiple_of_14():
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    tensor, model_size = dpt_v2(
        image,
        input_size=518,
        ensure_multiple_of=14,
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )
    assert tensor.shape == (1, 3, model_size[0], model_size[1])
    assert model_size[0] % 14 == 0
    assert model_size[1] % 14 == 0
    assert max(model_size) <= 518 + 14


def test_compute_depth_map_gradient(tmp_path):
    import cv2

    image = np.zeros((120, 160, 3), dtype=np.uint8)
    image[:] = (200, 200, 200)
    cv2.rectangle(image, (30, 20), (120, 90), (40, 40, 120), -1)

    depth_map, method = compute_depth_map(image, method="gradient_laplacian_v1")
    assert method == "gradient_laplacian_v1"
    assert depth_map.shape == (120, 160)
    assert depth_map.min() >= 0.0
    assert depth_map.max() <= 1.0


def test_depth_capabilities_payload(monkeypatch):
    monkeypatch.setattr(
        "geomora_multiview.depth_registry.available_models",
        lambda: {
            "depth_anything_v2_small_v1": False,
            "midas_v21_v1": False,
            "marigold_v1_1_v1": False,
        },
    )
    payload = depth_capabilities()
    assert payload["depth_auto"] == "gradient_laplacian_v1"
    assert "depth_anything_v2_small_v1" in payload["depth_models"]


def test_resolve_register_method_defaults_to_orb_without_colmap(monkeypatch):
    monkeypatch.setattr("geomora_multiview.pipeline.colmap_available", lambda: False)
    assert resolve_register_method("auto") == "feature_homography_v1"


def test_resolve_register_method_prefers_colmap_when_available(monkeypatch):
    monkeypatch.setattr("geomora_multiview.pipeline.colmap_available", lambda: True)
    assert resolve_register_method("auto") == "colmap_sparse_v1"


def test_multiview_capabilities_payload(monkeypatch):
    monkeypatch.setattr("geomora_multiview.pipeline.colmap_available", lambda: False)
    monkeypatch.setattr(
        "geomora_multiview.depth.depth_capabilities",
        lambda: {
            "depth_models": {
                "depth_anything_v2_small_v1": False,
                "midas_v21_v1": False,
                "marigold_v1_1_v1": False,
            },
            "depth_auto": "gradient_laplacian_v1",
            "depth_methods": ["auto", "gradient_laplacian_v1"],
        },
    )
    payload = multiview_capabilities()
    assert payload["colmap_available"] is False
    assert payload["depth_auto"] == "gradient_laplacian_v1"
    assert payload["depth_anything_available"] is False
    assert "feature_homography_v1" in payload["register_methods"]


def test_fuse_openings_records_depth_method(tmp_path):
    import cv2

    primary = tmp_path / "primary.jpg"
    secondary = tmp_path / "secondary.jpg"
    image = np.zeros((300, 400, 3), dtype=np.uint8)
    image[:] = (210, 210, 210)
    for x1, y1, x2, y2 in [(40, 70, 100, 160), (130, 70, 190, 160), (220, 70, 280, 160)]:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)
    transform = np.float32([[1, 0, 8], [0, 1, 6]])
    secondary_image = cv2.warpAffine(image, transform, (image.shape[1], image.shape[0]))
    cv2.imwrite(str(primary), image)
    cv2.imwrite(str(secondary), secondary_image)

    result = fuse_openings(
        str(primary),
        str(secondary),
        detect_method="contour_v1",
        depth_method="gradient_laplacian_v1",
        register_method="feature_homography_v1",
    )

    assert result.method == "multiview_fusion_v1"
    assert result.debug["depth_method"] == "gradient_laplacian_v1"
    assert result.debug["register_method"] == "feature_homography_v1"


def test_read_colmap_text_models(tmp_path):
    images_path = tmp_path / "images.txt"
    points_path = tmp_path / "points3D.txt"
    images_path.write_text(
        "\n".join(
            [
                "# Image list",
                "1 1 0 0 0 0 0 0 1 primary.jpg",
                "10.0 20.0 1 30.0 40.0 2",
                "2 1 0 0 0 0.1 0 0 1 secondary.jpg",
                "12.0 22.0 1 32.0 42.0 2",
            ]
        ),
        encoding="utf-8",
    )
    points_path.write_text(
        "\n".join(
            [
                "# 3D point",
                "1 0.0 0.0 1.0 255 0 0 0.1 1 0 2 1",
            ]
        ),
        encoding="utf-8",
    )

    images = read_images_text(images_path)
    points = read_points3d_text(points_path)

    assert len(images) == 2
    assert images[1].name == "primary.jpg"
    assert images[2].name == "secondary.jpg"
    assert len(points) == 1
    assert points[1].track == [(1, 0), (2, 1)]
