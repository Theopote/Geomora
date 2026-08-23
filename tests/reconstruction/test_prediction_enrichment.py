from __future__ import annotations

from geomora_reconstruct.ir_export import prediction_to_ir
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
