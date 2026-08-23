from __future__ import annotations

import json
from pathlib import Path

import pytest

from geomora_reconstruct.metrics import evaluate_reconstruction
from geomora_reconstruct.metrics import validate_ground_truth


HERE = Path(__file__).parent


def load(folder: str) -> dict:
    return json.loads((HERE / folder / "example_facade.json").read_text(encoding="utf-8"))


def test_full_reconstruction_metrics_have_objective_coverage():
    result = evaluate_reconstruction(load("ground_truth"), load("predictions"))
    assert result["detection"]["window"]["precision"] == 1.0
    assert result["topology"]["storey_accuracy"] == 1.0
    assert result["geometry"]["normalized_mae"] == 0.0
    assert result["scale"]["facade_width_mm_error"] == pytest.approx(0.05)
    assert result["rationalization"]["mean_improvement"] > 0.7
    assert result["sketchup"]["pass_rate"] == 1.0
    assert result["coverage"] == 1.0
    assert result["not_evaluated"] == []
    assert result["rqs"] > 90


def test_missing_annotations_are_not_silently_scored_as_success():
    truth = {"photo_id": "partial", "openings": []}
    prediction = {"photo_id": "partial", "openings": []}
    result = evaluate_reconstruction(truth, prediction)
    assert result["coverage"] == 0.25
    assert "topology" in result["not_evaluated"]
    assert "scale" in result["not_evaluated"]


def test_photo_ids_must_match():
    with pytest.raises(ValueError, match="photo_id"):
        evaluate_reconstruction({"photo_id": "a"}, {"photo_id": "b"})


def test_ground_truth_validation_is_available_at_metrics_boundary():
    report = validate_ground_truth(load("ground_truth"))
    assert report.valid is True
