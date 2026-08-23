from geomora_reconstruct.metrics.constraint_solver_metrics import evaluate_constraint_solver


def _prediction(solved):
    return {
        "topology": {"facade_bbox": [0, 0, 1, 1]},
        "openings": [
            {"id": "a", "observed_bbox": [0.1, 0.1, 0.3, 0.3], "bbox": solved[0]},
            {"id": "b", "observed_bbox": [0.4, 0.1, 0.6, 0.3], "bbox": solved[1]},
        ],
        "constraint_solution": {
            "mean_residual_before": 0.1,
            "mean_residual_after": 0.02,
            "constraints": [
                {"priority": "soft", "satisfied": True},
                {"priority": "hard", "satisfied": True},
            ],
        },
    }


def test_constraint_solver_metrics_measure_improvement_and_drift():
    metrics = evaluate_constraint_solver(_prediction(([0.11, 0.1, 0.31, 0.3], [0.39, 0.1, 0.59, 0.3])))

    assert metrics["residual_reduction"] == 0.8
    assert metrics["hard_satisfaction_rate"] == 1.0
    assert metrics["mean_bbox_drift"] == 0.005
    assert metrics["introduced_overlaps"] == 0


def test_constraint_solver_metrics_detect_new_overlap_and_boundary_violation():
    prediction = _prediction(([0.1, 0.1, 0.45, 0.3], [0.4, 0.1, 1.1, 0.3]))
    prediction["constraint_solution"]["constraints"][1]["satisfied"] = False
    metrics = evaluate_constraint_solver(prediction)

    assert metrics["introduced_overlaps"] == 1
    assert metrics["introduced_boundary_violations"] == 1
    assert metrics["hard_violations"] == 1
