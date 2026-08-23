from __future__ import annotations

from geomora_reconstruct.ir_export import attach_metric_block, prediction_to_ir
from geomora_reconstruct.rationalization_variance import attach_rationalization_metrics
from geomora_reconstruct.sketchup_checks import attach_sketchup_checks


def test_enrichment_adds_rationalization_sketchup_and_ir():
    prediction = {
        "photo_id": "photo_test",
        "topology": {"storey_count": 2, "bay_count": 2, "facade_bbox": [0.0, 0.0, 1.0, 1.0]},
        "openings": [
            {"id": "w1", "type": "window", "bbox": [0.10, 0.12, 0.30, 0.36], "storey": 2, "bay": 1, "confidence": 0.8},
            {"id": "w2", "type": "window", "bbox": [0.62, 0.12, 0.82, 0.36], "storey": 2, "bay": 2, "confidence": 0.8},
            {"id": "w3", "type": "window", "bbox": [0.10, 0.58, 0.30, 0.82], "storey": 1, "bay": 1, "confidence": 0.8},
            {"id": "w4", "type": "window", "bbox": [0.62, 0.58, 0.82, 0.82], "storey": 1, "bay": 2, "confidence": 0.8},
        ],
        "pipeline": {
            "scale_hint": {
                "wall_length_mm": 10000,
                "wall_height_mm": 6000,
                "method": "window_sill",
                "confidence": 0.75,
            }
        },
    }

    attach_rationalization_metrics(prediction)
    attach_sketchup_checks(prediction)
    ir = prediction_to_ir(prediction)

    assert prediction["rationalization_before"]["width_variance"] >= 0.0
    assert prediction["rationalization_after"]["width_variance"] <= prediction["rationalization_before"]["width_variance"]
    assert prediction["sketchup"]["generate_stable"] is True
    assert ir is not None
    assert len(ir["openings"]) == 4


def test_ir_uses_facade_coordinates_and_millimetre_opening_geometry():
    prediction = {
        "photo_id": "anchored",
        "facade": {"bbox": [0.1, 0.1, 0.9, 0.9]},
        "topology": {"storey_count": 2, "bay_count": 1, "facade_bbox": [0.1, 0.1, 0.9, 0.9]},
        "openings": [
            {"id": "w1", "type": "window", "bbox": [0.2, 0.5, 0.4, 0.74], "storey": 1}
        ],
        "metric_anchors": [
            {"id": "anchor_facade_width", "axis": "horizontal", "start": [0.1, 0.9], "end": [0.9, 0.9], "distance_mm": 12000},
            {"id": "anchor_facade_height", "axis": "vertical", "start": [0.1, 0.1], "end": [0.1, 0.9], "distance_mm": 6000},
        ],
        "pipeline": {"scale_hint": {"wall_length_mm": 4000, "wall_height_mm": 2400}},
    }

    ir = prediction_to_ir(prediction)

    assert ir is not None
    assert ir["metric_source"] == "metric_anchor"
    assert ir["metric"]["facade_width_mm"] == 12000
    opening = ir["openings"][0]["geometry"]
    assert opening["offset"] == 1500
    assert opening["width"] == 3000
    assert opening["height"] == 1800
    assert opening["sill_height"] == 1200


def test_attach_metric_block_does_not_replace_explicit_metric_with_scale_hint():
    prediction = {
        "topology": {"storey_count": 2},
        "openings": [],
        "metric": {"facade_width_mm": 11000, "facade_height_mm": 7000},
        "metric_source": "user_anchor",
        "pipeline": {"scale_hint": {"wall_length_mm": 4000, "wall_height_mm": 2400}},
    }

    metric = attach_metric_block(prediction)

    assert metric == {
        "facade_width_mm": 11000.0,
        "facade_height_mm": 7000.0,
        "storey_height_mm": 3500.0,
    }
    assert prediction["metric_source"] == "user_anchor"


def test_width_only_anchor_blends_with_weak_height_without_losing_anchor():
    prediction = {
        "photo_id": "width_only",
        "topology": {"storey_count": 2},
        "openings": [],
        "metric_anchors": [
            {"id": "facade_width", "axis": "horizontal", "distance_mm": 12000}
        ],
        "pipeline": {"scale_hint": {"wall_length_mm": 4000, "wall_height_mm": 6000}},
    }

    metric = attach_metric_block(prediction)
    ir = prediction_to_ir(prediction)

    assert metric["facade_width_mm"] == 12000
    assert metric["facade_height_mm"] == 6000
    assert prediction["metric_source"] == "metric_anchor_blended"
    assert ir is not None
    assert ir["metric_source"] == "metric_anchor_blended"
