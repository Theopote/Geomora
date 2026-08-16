from __future__ import annotations

import cv2
import numpy as np
import pytest

from geomora_detect.sam_onnx import (
    bbox_norm_to_sam_box,
    mask_to_bbox_norm,
    mobile_sam_available,
    preprocess_shape,
    preprocess_image,
)


def test_preprocess_shape():
    new_h, new_w = preprocess_shape(600, 800, 1024)
    assert new_h == 768
    assert new_w == 1024


def test_bbox_norm_to_sam_box():
    coords = bbox_norm_to_sam_box(
        [0.1, 0.2, 0.3, 0.4],
        original_size=(600, 800),
        resized_size=(768, 1024),
    )
    assert coords.shape == (1, 2, 2)
    assert coords[0, 0, 0] < coords[0, 1, 0]
    assert coords[0, 0, 1] < coords[0, 1, 1]


def test_mask_to_bbox_norm():
    mask = np.zeros((100, 200), dtype=np.float32)
    mask[20:40, 30:80] = 1.0
    bbox = mask_to_bbox_norm(mask, resized_size=(100, 200))
    assert bbox is not None
    assert bbox[0] == pytest.approx(0.15, abs=0.02)
    assert bbox[2] == pytest.approx(0.4, abs=0.02)


@pytest.mark.skipif(not mobile_sam_available(), reason="MobileSAM ONNX models not downloaded")
def test_mobile_sam_runner_on_synthetic():
    from geomora_detect.sam_onnx import MobileSamOnnxRunner

    image = np.full((600, 800, 3), (210, 210, 210), dtype=np.uint8)
    cv2.rectangle(image, (20, 40), (780, 560), (175, 168, 158), -1)
    cv2.rectangle(image, (80, 140), (200, 320), (35, 35, 120), -1)

    runner = MobileSamOnnxRunner.from_config()
    runner.encode(image)
    mask, bbox = runner.predict_mask_from_box([0.10, 0.23, 0.25, 0.53])
    assert bbox is not None
    assert mask is not None
    assert bbox[2] > bbox[0]
    assert bbox[3] > bbox[1]
