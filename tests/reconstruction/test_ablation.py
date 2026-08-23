from __future__ import annotations

from geomora_detect.models import DetectedElement, DetectionResult
from geomora_reconstruct.ablation import (
    build_stage_predictions, build_vlm_pair_predictions, evaluate_stages,
    summarize_stage, summarize_vlm_pair,
)
from geomora_reconstruct.vlm_evidence import parse_architectural_evidence


def _detection():
    return DetectionResult(
        method="fixture", confidence=0.8, image_width=1000, image_height=800,
        elements=[
            DetectedElement("window", [0.1, 0.2, 0.25, 0.4], 0.9),
            DetectedElement("window", [0.5, 0.2, 0.65, 0.4], 0.9),
        ],
    )


def _evidence():
    return parse_architectural_evidence({
        "building_type": {"value": "masonry", "confidence": 0.9},
        "facade": {"bbox": [0, 0, 1, 1], "visible_storeys": {"value": 2, "confidence": 0.9},
                   "bay_count": {"value": 2, "confidence": 0.9},
                   "repetition": {"value": "strong", "confidence": 0.8}},
        "opening_groups": [], "occlusions": [], "uncertainties": [],
    }, photo_id="fixture", provider="openai", model="cached")


def test_ablation_stages_are_isolated_and_monotonic_in_capability():
    stages = build_stage_predictions(
        "fixture", _detection(), evidence=_evidence(),
        metric_anchors=[
            {"id": "width", "type": "facade_width", "target": "facade",
             "property": "width", "priority": "hard", "distance_mm": 10000},
            {"id": "height", "type": "facade_height", "target": "facade",
             "property": "height", "priority": "hard", "distance_mm": 6000},
        ],
    )
    assert "topology" not in stages["A_cv"]
    assert stages["B_cv_vlm"]["topology"]["method"] == "vlm_raw_evidence_no_understanding"
    assert stages["B_cv_vlm"]["openings"][0].get("storey") is None
    assert stages["C_understanding"]["topology"]["method"] == "understanding_v0.2_evidence"
    assert "metric" not in stages["C_understanding"]
    assert stages["D_metric_anchor"]["metric"]["facade_width_mm"] == 10000
    assert "constraint_solution" not in stages["D_metric_anchor"]
    assert "constraint_solution" in stages["E_constraint_solver"]
    assert "architectural_ir" in stages["E_constraint_solver"]


def test_ablation_reports_rqs_coverage_and_fixed_components():
    truth = {
        "schema_version": "reconstruction-metrics-v1", "photo_id": "fixture",
        "facade": {"width": 1, "height": 1}, "topology": {"storey_count": 2, "bay_count": 2},
        "openings": [
            {"id": "w1", "type": "window", "bbox": [0.1, 0.2, 0.25, 0.4], "storey": 1, "bay": 1},
            {"id": "w2", "type": "window", "bbox": [0.5, 0.2, 0.65, 0.4], "storey": 1, "bay": 2},
        ],
        "metric": {"facade_width_mm": 10000},
    }
    predictions = build_stage_predictions("fixture", _detection(), evidence=_evidence())
    metrics = evaluate_stages(truth, predictions)
    rows = [{"photo_id": "fixture", "split": "train", "metrics": metrics["A_cv"]}]
    summary = summarize_stage("A_cv", rows)
    assert summary["mean_rqs"] is not None
    assert summary["mean_coverage"] < 1.0
    assert summary["storey_accuracy"] is None

    pair = build_vlm_pair_predictions("fixture", _detection(), evidence=_evidence())
    pair_metrics = evaluate_stages(truth, pair)
    paired_summary = summarize_vlm_pair({
        arm: [{"photo_id": "fixture", "split": "train", "metrics": pair_metrics[arm]}]
        for arm in pair
    })
    assert paired_summary["comparison"] == "same_detection_same_understanding"
    assert "storey_accuracy" in paired_summary["delta_with_minus_without"]
