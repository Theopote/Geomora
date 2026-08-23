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
