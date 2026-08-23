from __future__ import annotations

import pytest

from geomora_reconstruct.constraints import solve_opening_constraints, solve_prediction_constraints
from geomora_reconstruct.prediction_enrichment import enrich_prediction


OPENINGS = [
    {"id": "w1", "type": "window", "bbox": [0.10, 0.20, 0.19, 0.42], "storey": 1, "bay": 1},
    {"id": "w2", "type": "window", "bbox": [0.32, 0.18, 0.44, 0.40], "storey": 1, "bay": 2},
    {"id": "w3", "type": "window", "bbox": [0.57, 0.22, 0.67, 0.43], "storey": 1, "bay": 3},
]


def constraint(kind: str, *, priority: str = "soft", confidence: float = 0.9, weight: float = 0.9):
    return {"id": f"c_{kind}", "type": kind, "targets": ["w1", "w2", "w3"], "priority": priority, "confidence": confidence, "weight": weight, "status": "proposed"}


def test_soft_constraints_reduce_residual_and_preserve_observations():
    result = solve_opening_constraints(
        OPENINGS,
        [constraint("equal_width"), constraint("equal_height"), constraint("align"), constraint("equal_spacing")],
    )
    assert result["mean_residual_after"] < result["mean_residual_before"]
    assert result["hard_violations"] == []
    assert result["openings"][0]["observed_bbox"] == OPENINGS[0]["bbox"]
    assert result["openings"][0]["bbox"] != OPENINGS[0]["bbox"]
    assert OPENINGS[0].get("observed_bbox") is None


def test_hard_constraint_is_satisfied_exactly():
    result = solve_opening_constraints(OPENINGS, [constraint("equal_width", priority="hard")])
    widths = [item["bbox"][2] - item["bbox"][0] for item in result["openings"]]
    assert widths == pytest.approx([widths[0]] * 3, abs=1e-6)
    assert result["constraints"][0]["satisfied"] is True


def test_unknown_targets_are_ignored_without_creating_geometry():
    invalid = {**constraint("equal_width"), "targets": ["missing_a", "missing_b"]}
    result = solve_opening_constraints(OPENINGS, [invalid])
    assert [item["bbox"] for item in result["openings"]] == [item["bbox"] for item in OPENINGS]


def test_prediction_enrichment_applies_solution_before_ir_export():
    prediction = {
        "photo_id": "solver",
        "facade": {"width": 1.0, "height": 1.0},
        "topology": {"storey_count": 1, "bay_count": 3, "facade_bbox": [0, 0, 1, 1], "pattern_groups": []},
        "openings": [dict(item) for item in OPENINGS],
        "constraint_suggestions": [constraint("equal_width"), constraint("align")],
        "pipeline": {"scale_hint": {"wall_length_mm": 10000, "wall_height_mm": 3000}},
    }
    enrich_prediction(prediction, export_ir=True)
    assert prediction["constraint_solution"]["method"] == "weighted_projection_v0.1"
    assert prediction["architectural_ir"]["constraints"]
    assert all("observed_bbox" in item for item in prediction["openings"])
    assert prediction["rationalization_after"]["width_variance"] < prediction["rationalization_before"]["width_variance"]


def test_user_metric_anchor_is_exported_as_hard_fixed_dimension():
    prediction = {
        "photo_id": "anchored_solver",
        "facade": {"width": 1.0, "height": 1.0},
        "topology": {"storey_count": 2, "bay_count": 1, "facade_bbox": [0, 0, 1, 1]},
        "openings": [dict(OPENINGS[0])],
        "metric_anchors": [
            {"id": "facade_width", "axis": "horizontal", "distance_mm": 12000},
            {"id": "facade_height", "axis": "vertical", "distance_mm": 7000},
        ],
    }
    enrich_prediction(prediction, export_ir=True)
    constraints = prediction["architectural_ir"]["constraints"]
    hard = [item for item in constraints if item["priority"] == "hard"]
    assert len(hard) == 2
    assert all(item["type"] == "fixed_dimension" for item in hard)
    assert hard[0]["source"] == "user_anchor"
    assert prediction["architectural_ir"]["metric"]["facade_width_mm"] == 12000
