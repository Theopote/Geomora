from __future__ import annotations

import pytest

from geomora_detect.acceptance_metrics import (
    bbox_iou,
    evaluate_elements,
    match_class_boxes,
    parse_yolo_label_file,
    yolo_line_to_bbox_norm,
)
from geomora_detect.models import DetectedElement


def test_yolo_line_to_bbox_norm():
    parsed = yolo_line_to_bbox_norm("0 0.175 0.38 0.15 0.30")
    assert parsed is not None
    class_name, bbox = parsed
    assert class_name == "window"
    assert bbox == pytest.approx([0.10, 0.23, 0.25, 0.53], abs=1e-6)


def test_bbox_iou_full_overlap():
    box = [0.1, 0.2, 0.3, 0.4]
    assert bbox_iou(box, box) == pytest.approx(1.0)


def test_match_class_boxes_counts_tp_fp_fn():
    metrics = match_class_boxes(
        predictions=[[0.10, 0.23, 0.25, 0.53], [0.50, 0.20, 0.60, 0.40]],
        ground_truth=[[0.10, 0.23, 0.25, 0.53]],
        iou_threshold=0.5,
    )
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 0


def test_evaluate_elements_passes_good_prediction():
    elements = [
        DetectedElement(type="window", bbox_norm=[0.10, 0.23, 0.25, 0.53], confidence=0.9),
        DetectedElement(type="door", bbox_norm=[0.01, 0.55, 0.09, 0.93], confidence=0.8),
    ]
    ground_truth = [
        ("window", [0.10, 0.23, 0.25, 0.53]),
        ("door", [0.01, 0.55, 0.09, 0.93]),
    ]
    metrics, passed, notes = evaluate_elements(elements, ground_truth)
    assert passed is True
    assert notes == []
    assert metrics["window"].recall == 1.0
    assert metrics["door"].recall == 1.0


def test_parse_yolo_label_file(tmp_path):
    label_path = tmp_path / "sample.txt"
    label_path.write_text("0 0.175 0.38 0.15 0.30\n1 0.05 0.74 0.08 0.38\n", encoding="utf-8")
    boxes = parse_yolo_label_file(label_path)
    assert len(boxes) == 2
    assert boxes[0][0] == "window"
