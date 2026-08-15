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
