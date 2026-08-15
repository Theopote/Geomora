from __future__ import annotations

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from geomora_rectify.server import app


def _facade_image() -> np.ndarray:
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    image[:] = (210, 210, 210)
    cv2.rectangle(image, (80, 60), (720, 540), (175, 168, 158), -1)
    cv2.rectangle(image, (120, 140), (220, 320), (35, 35, 120), -1)
    return image


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_multiview_register_endpoint(client: TestClient, tmp_path):
    primary = tmp_path / "primary.jpg"
    secondary = tmp_path / "secondary.jpg"
    cv2.imwrite(str(primary), _facade_image())
    shifted = _facade_image()
    shifted = np.roll(shifted, 15, axis=1)
    cv2.imwrite(str(secondary), shifted)

    with primary.open("rb") as primary_file, secondary.open("rb") as secondary_file:
        response = client.post(
            "/multiview/register",
            files={
                "primary": ("primary.jpg", primary_file, "image/jpeg"),
                "secondary": ("secondary.jpg", secondary_file, "image/jpeg"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "feature_homography_v1"
    assert payload["match_count"] > 0
    assert len(payload["views"]) == 2
