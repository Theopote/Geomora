from __future__ import annotations

from geomora_reconstruct.export import detection_to_prediction
from geomora_reconstruct.geometry_inference import attach_geometry_to_openings, opening_geometry_ratios
from geomora_reconstruct.metrics import evaluate_reconstruction
from geomora_detect.models import DetectedElement, DetectionResult


def test_opening_geometry_ratios_use_topology_storeys():
    opening = {"id": "w11", "type": "window", "bbox": [0.10, 0.58, 0.30, 0.82], "storey": 1}
    facade = {"width": 1.0, "height": 1.0}
    topology = {"storey_count": 2, "bay_count": 2}

    ratios = opening_geometry_ratios(opening, facade, topology)

    assert ratios["width_facade"] == 0.2
    assert ratios["height_storey"] == 0.48
    assert ratios["sill_storey"] == 0.64


def test_detection_to_prediction_attaches_geometry_block():
    detection = DetectionResult(
        method="auto_fusion_v1",
        confidence=0.8,
        image_width=800,
        image_height=600,
        elements=[
            DetectedElement(type="window", bbox_norm=[0.10, 0.12, 0.30, 0.36], confidence=0.8),
            DetectedElement(type="window", bbox_norm=[0.60, 0.12, 0.80, 0.36], confidence=0.8),
        ],
    )
    payload = detection_to_prediction("photo_test", detection)

    assert payload["topology"]["storey_count"] == 1
    assert payload["geometry"]["method"] == "bbox_ratios_v0.1"
    assert payload["openings"][0]["geometry"]["width_facade"] == 0.2


def test_detection_to_prediction_carries_runtime_metric_anchors():
    detection = DetectionResult(
        method="test",
        confidence=0.8,
        image_width=800,
        image_height=600,
        elements=[],
    )
    anchors = [{"id": "facade_width", "axis": "horizontal", "distance_mm": 12000}]

    payload = detection_to_prediction("anchored", detection, metric_anchors=anchors)

    assert payload["metric_anchors"] == anchors
    assert payload["metric_anchors"] is not anchors


def test_geometry_metrics_match_by_iou_not_id():
    truth = {
        "photo_id": "pair",
        "facade": {"width": 1.0, "height": 1.0},
        "topology": {"storey_count": 1, "bay_count": 1},
        "openings": [
            {"id": "w11", "type": "window", "bbox": [0.10, 0.20, 0.30, 0.40]},
        ],
    }
    prediction = {
        "photo_id": "pair",
        "facade": {"width": 1.0, "height": 1.0},
        "topology": {"storey_count": 1, "bay_count": 1},
        "openings": [
            {
                "id": "pred_001",
                "type": "window",
                "bbox": [0.10, 0.20, 0.30, 0.40],
                "geometry": {"width_facade": 0.2, "height_storey": 0.2, "sill_storey": 0.6},
            }
        ],
        "geometry": {"method": "bbox_ratios_v0.1", "opening_count": 1},
    }

    result = evaluate_reconstruction(truth, prediction)

    assert result["geometry"]["matched_openings"] == 1
    assert result["geometry"]["normalized_mae"] == 0.0
