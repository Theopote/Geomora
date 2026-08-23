from geomora_reconstruct.reconstruction_audit import extract_audit_event, summarize_audit


def _ir(status, decision=None):
    reconstruction = {"constraint_solver": {"safety_status": status, "human_review_required": status != "accepted", "attempt_count": 2, "soft_weight_scale": 0.25}}
    if decision:
        reconstruction["review"] = {"decision": decision, "reviewed_at": "2026-08-23T12:00:00Z"}
    return {"reconstruction": reconstruction}


def test_extracts_structured_review_without_geometry():
    event = extract_audit_event(_ir("fallback_observed_geometry", "accepted_manual_adjustments"), artifact_id="photo_1", split="val")
    assert event["review_completed"] is True
    assert event["manual_adjustment"] is True
    assert "openings" not in event


def test_summary_seals_holdout_from_tuning_statistics():
    events = [
        extract_audit_event(_ir("accepted"), artifact_id="train", split="train"),
        extract_audit_event(_ir("accepted_after_soft_weight_retry", "accepted_observed_geometry"), artifact_id="val", split="val"),
        extract_audit_event(_ir("fallback_observed_geometry", "accepted_manual_adjustments"), artifact_id="secret", split="holdout"),
    ]
    summary = summarize_audit(events)
    assert summary["operational"]["solver_events"] == 2
    assert summary["tuning_eligible"]["solver_events"] == 2
    assert summary["tuning_eligible"]["fallback_rate"] == 0.0
    assert summary["holdout_sealed"] == {"solver_events": 1, "details_exposed": False, "use": "gate_only_not_for_tuning"}


def test_audit_counts_uncertainty_decisions_without_geometry():
    document = _ir("accepted")
    document["reconstruction"]["uncertainty_review"] = {
        "decisions": [
            {"decision": "accepted_ai", "opening_id": "pred_001"},
            {"decision": "manual_edit", "opening_id": "pred_002"},
        ],
        "summary": {"accepted_ai": 1, "manual_edit": 1},
    }

    event = extract_audit_event(document, artifact_id="photo_2", split="val")
    assert event["uncertainty_decision_count"] == 2
    assert event["uncertainty_manual_edit_count"] == 1
    assert "decisions" not in event
