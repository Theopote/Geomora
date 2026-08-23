"""Privacy-conscious operational audit for reconstruction solver decisions."""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

REVIEW_STATUSES = {"accepted_after_soft_weight_retry", "fallback_observed_geometry"}
APPROVED_DECISIONS = {"accepted_observed_geometry", "accepted_manual_adjustments"}


def extract_audit_event(document: dict[str, Any], *, artifact_id: str, split: str = "unknown") -> dict[str, Any] | None:
    reconstruction = document.get("reconstruction") or {}
    solver = reconstruction.get("constraint_solver")
    if not isinstance(solver, dict):
        return None
    review = reconstruction.get("review") or {}
    status = solver.get("safety_status", "unknown")
    decision = review.get("decision")
    return {
        "artifact_id": artifact_id,
        "split": split,
        "solver_status": status,
        "review_required": bool(solver.get("human_review_required", status in REVIEW_STATUSES)),
        "review_decision": decision,
        "review_completed": decision in APPROVED_DECISIONS,
        "manual_adjustment": decision == "accepted_manual_adjustments",
        "retry_requested": decision == "retry_constraints_requested",
        "attempt_count": int(solver.get("attempt_count", 0) or 0),
        "soft_weight_scale": solver.get("soft_weight_scale"),
        "fallback_reasons": list(solver.get("fallback_reasons") or []),
        "reviewed_at": review.get("reviewed_at"),
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(event["solver_status"] for event in events)
    decisions = Counter(event["review_decision"] for event in events if event.get("review_decision"))
    review_required = sum(event["review_required"] for event in events)
    review_completed = sum(event["review_completed"] for event in events if event["review_required"])
    total = len(events)
    return {
        "solver_events": total,
        "status_counts": dict(sorted(statuses.items())),
        "decision_counts": dict(sorted(decisions.items())),
        "automatic_pass_rate": _rate(statuses["accepted"], total),
        "reduced_weight_rate": _rate(statuses["accepted_after_soft_weight_retry"], total),
        "fallback_rate": _rate(statuses["fallback_observed_geometry"], total),
        "review_completion_rate": _rate(review_completed, review_required),
        "manual_adjustment_rate": _rate(sum(event["manual_adjustment"] for event in events), review_completed),
        "retry_request_rate": _rate(sum(event["retry_requested"] for event in events), review_required),
    }


def summarize_audit(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(events)
    operational = [event for event in rows if event.get("split") != "holdout"]
    tuning = [event for event in rows if event.get("split") in ("train", "val")]
    holdout = [event for event in rows if event.get("split") == "holdout"]
    return {
        "operational": _summary(operational),
        "tuning_eligible": _summary(tuning),
        "holdout_sealed": {"solver_events": len(holdout), "details_exposed": False, "use": "gate_only_not_for_tuning"},
    }
