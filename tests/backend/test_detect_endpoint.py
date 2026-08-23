from __future__ import annotations

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from geomora_rectify.server import app


def _synthetic_rectified_facade(width: int = 800, height: int = 600) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (210, 210, 210)
    for x1, y1, x2, y2 in [(80, 140, 200, 320), (240, 140, 360, 320)]:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)
    return image


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_detect_endpoint_contour(client: TestClient, tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "facade.jpg"
    cv2.imwrite(str(path), image)

    with path.open("rb") as handle:
        response = client.post(
            "/detect",
            files={"image": ("facade.jpg", handle, "image/jpeg")},
            data={"method": "contour_v1"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "contour_v1"
    assert payload["image_width"] == 800
    assert len(payload["elements"]) >= 2


def test_reconstruct_endpoint_returns_evidence_understanding_and_ir(client: TestClient, tmp_path):
    image = _synthetic_rectified_facade()
    path = tmp_path / "facade.jpg"
    cv2.imwrite(str(path), image)

    with path.open("rb") as handle:
        response = client.post(
            "/reconstruct",
            files={"image": ("facade.jpg", handle, "image/jpeg")},
            data={
                "method": "contour_v1",
                "photo_id": "workspace_test",
                "wall_length_mm": "12000",
                "wall_height_mm": "7200",
                "depth_method": "gradient_laplacian_v1",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "geomora-reconstruction-v0.1"
    assert payload["photo_id"] == "workspace_test"
    assert payload["observation_graph"]["observations"]
    assert payload["understanding"]["opening_count"] >= 2
    assert payload["understanding"]["storeys"]
    assert payload["understanding"]["bays"]
    assert payload["understanding"]["facade_bbox"]
    assert payload["architectural_ir"]["metric"]["facade_width_mm"] == 12000
    assert payload["status"] == "ready"
    assert payload["depth_evidence"]["used"] is True
    assert payload["depth_evidence"]["method"] == "gradient_laplacian_v1"
    assert payload["depth_evidence"]["metric_depth_evidence"] is False
    assert payload["observation_graph"]["debug"]["depth_discontinuity"]["adapter"] == "depth_discontinuity_v0.1"


def test_cloud_reconstruction_requires_per_upload_authorization(client: TestClient, tmp_path):
    path = tmp_path / "facade.jpg"
    cv2.imwrite(str(path), _synthetic_rectified_facade())
    with path.open("rb") as handle:
        response = client.post(
            "/reconstruct",
            files={"image": ("facade.jpg", handle, "image/jpeg")},
            data={"method": "contour_v1", "routing_mode": "cloud_enhanced", "vlm_provider": "openai"},
        )
    assert response.status_code == 200
    assert response.json()["cloud_evidence"] == {
        "requested": True,
        "used": False,
        "provider": "openai",
        "status": "authorization_required",
    }
