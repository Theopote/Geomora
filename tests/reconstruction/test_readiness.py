from geomora_reconstruct.readiness import derive_reconstruction_readiness


def _prediction(**overrides):
    value = {
        "topology": {"storey_count": 1},
        "openings": [{"id": "w1"}],
        "constraint_solution": {"safety_status": "accepted", "constraint_status": "satisfied"},
        "architectural_ir": {"schema_version": "0.1"},
    }
    value.update(overrides)
    return value


def test_clean_ir_is_ready_to_generate():
    result = derive_reconstruction_readiness(_prediction())
    assert result["pipeline_stage"] == "ir_ready"
    assert result["readiness"] == "ready_to_generate"
    assert result["ready_to_generate"] is True
    assert result["blockers"] == []


def test_ir_existence_does_not_hide_review_blockers():
    prediction = _prediction(constraint_solution={
        "safety_status": "fallback_observed_geometry",
        "constraint_status": "fallback",
        "fallback_reasons": ["introduced_overlap"],
    })
    result = derive_reconstruction_readiness(prediction, uncertainties=[{"code": "low_confidence"}])
    assert result["readiness"] == "needs_review"
    assert result["ready_to_generate"] is False
    assert {item["code"] for item in result["blockers"]} == {
        "uncertain_reconstruction", "solver_fallback"
    }


def test_missing_ir_has_scale_precedence_even_when_review_is_needed():
    result = derive_reconstruction_readiness(
        _prediction(architectural_ir=None),
        architectural_hypotheses=[{"id": "storey_1", "requires_confirmation": True}],
    )
    assert result["pipeline_stage"] == "solved"
    assert result["readiness"] == "needs_scale"
    assert {item["code"] for item in result["blockers"]} == {
        "metric_scale_missing", "architectural_hypothesis_pending"
    }


def test_hard_constraint_failure_is_blocking():
    result = derive_reconstruction_readiness(_prediction(constraint_solution={
        "safety_status": "accepted",
        "constraint_status": "failed",
        "hard_violations": ["anchor_001"],
    }))
    assert result["readiness"] == "needs_review"
    assert result["blockers"][0]["code"] == "hard_constraint_unsatisfied"


def test_vlm_cv_conflict_is_blocking():
    prediction = _prediction()
    prediction["topology"]["evidence_coordination"] = {"storey_count": {"conflict": True}}
    result = derive_reconstruction_readiness(prediction)
    assert result["readiness"] == "needs_review"
    assert result["blockers"][0]["code"] == "vlm_cv_conflict"
