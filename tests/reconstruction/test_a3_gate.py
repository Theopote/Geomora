from __future__ import annotations

import json
from pathlib import Path

from geomora_reconstruct.metrics.a3_gate import evaluate_a3_gate
from geomora_reconstruct.prediction_enrichment import enrich_prediction
from geomora_reconstruct.metrics import evaluate_reconstruction

HERE = Path(__file__).parent


def _load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def test_a3_gate_passes_on_full_example_fixture():
    minimal_set = {
        "photos": [
            {"id": "example_facade", "split": "val"},
        ]
    }
    truth = _load("ground_truth/example_facade.json")
    truth = {
        **truth,
        "annotation_status": "reviewed_v1",
        "review_rounds": 2,
    }
    prediction = _load("predictions/example_facade.json")
    enrich_prediction(prediction)
    metrics = evaluate_reconstruction(truth, prediction)
    results = [{"photo_id": "example_facade", "split": "val", "metrics": metrics}]
    report = evaluate_a3_gate(minimal_set, results, truths={"example_facade": truth}, phase="stage_a_core")

    assert report.summary["mean_rqs"] is not None
    assert report.summary["mean_coverage"] == 1.0
    assert any(check.id == "val_window_recall" for check in report.checks)


def test_a3_gate_fails_when_metrics_missing():
    minimal_set = {"photos": [{"id": "photo_01", "split": "train"}]}
    report = evaluate_a3_gate(minimal_set, [{"photo_id": "photo_01", "split": "train", "metrics": None}])

    assert report.passed is False
    assert "missing_metrics:photo_01" in report.blockers


def test_a3_gate_blocks_unsafe_constraint_solver_output():
    minimal_set = {"photos": [{"id": "photo_01", "split": "val"}]}
    metrics = {
        "rqs": 100.0,
        "coverage": 1.0,
        "detection": {"window": {"recall": 1.0}},
        "topology": {"storey_accuracy": 1.0},
        "geometry": {"normalized_mae": 0.0},
        "sketchup": {"pass_rate": 1.0},
        "constraint_solver": {
            "residual_reduction": -0.1,
            "hard_satisfaction_rate": 0.5,
            "mean_bbox_drift": 0.04,
            "max_bbox_drift": 0.2,
            "introduced_overlaps": 1,
            "introduced_boundary_violations": 0,
        },
    }
    report = evaluate_a3_gate(minimal_set, [{"photo_id": "photo_01", "metrics": metrics}], phase="stage_a_core")

    solver_checks = {check.id: check for check in report.checks if check.id.startswith("solver_")}
    assert report.passed is False
    assert set(solver_checks) == {
        "solver_residual_reduction",
        "solver_hard_satisfaction",
        "solver_geometry_drift",
        "solver_introduced_violations",
    }
    assert all(not check.passed for check in solver_checks.values())


def test_stage_a_full_requires_constraint_solver_metrics():
    minimal_set = {"photos": [{"id": "photo_01", "split": "val"}]}
    metrics = {
        "rqs": 100.0,
        "coverage": 1.0,
        "detection": {"window": {"recall": 1.0}},
        "topology": {"storey_accuracy": 1.0},
        "geometry": {"normalized_mae": 0.0},
        "sketchup": {"pass_rate": 1.0},
    }
    report = evaluate_a3_gate(minimal_set, [{"photo_id": "photo_01", "metrics": metrics}], phase="stage_a_full")

    assert "missing_constraint_solver_metrics" in report.blockers


def test_a3_gate_blocks_internally_inconsistent_ground_truth():
    truth = _load("ground_truth/photo_19.json")
    w291 = next(item for item in truth["openings"] if item["id"] == "w291")
    w291.update(storey=1, bay=1)
    truth["pattern_groups"][0]["members"].remove("w291")
    minimal_set = {"photos": [{"id": "photo_19", "split": "val"}]}
    metrics = {"rqs": 100.0, "coverage": 1.0, "detection": {"window": {"recall": 1.0}}, "topology": {"storey_accuracy": 1.0}, "geometry": {"normalized_mae": 0.0}, "sketchup": {"pass_rate": 1.0}}
    report = evaluate_a3_gate(minimal_set, [{"photo_id": "photo_19", "metrics": metrics}], truths={"photo_19": truth})
    assert report.passed is False
    assert any(blocker.startswith("ground_truth_inconsistent:photo_19") for blocker in report.blockers)
