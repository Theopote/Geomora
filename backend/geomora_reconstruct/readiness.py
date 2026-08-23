"""Derive product-facing reconstruction readiness from pipeline evidence."""
from __future__ import annotations

from typing import Any


REVIEW_SOLVER_STATUSES = {
    "accepted_after_soft_weight_retry": "solver_soft_retry",
    "fallback_observed_geometry": "solver_fallback",
}


def _blocker(code: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "severity": "blocking", "message": message}
    if details:
        item["details"] = details
    return item


def derive_reconstruction_readiness(
    prediction: dict[str, Any],
    *,
    uncertainties: list[Any] | None = None,
    architectural_hypotheses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return one authoritative stage/readiness decision for API and UI consumers."""
    topology = prediction.get("topology") or {}
    solution = prediction.get("constraint_solution") or {}
    ir = prediction.get("architectural_ir")
    blockers: list[dict[str, Any]] = []

    if not ir:
        blockers.append(_blocker("metric_scale_missing", "A valid metric scale is required before generation."))

    pending_uncertainties = list(uncertainties or topology.get("uncertainties") or [])
    if pending_uncertainties:
        blockers.append(_blocker(
            "uncertain_reconstruction",
            "Uncertain reconstruction evidence requires review.",
            details={"count": len(pending_uncertainties)},
        ))

    hypotheses = [item for item in (architectural_hypotheses or []) if item.get("requires_confirmation", True)]
    if hypotheses:
        blockers.append(_blocker(
            "architectural_hypothesis_pending",
            "Architectural hypotheses require confirmation.",
            details={"count": len(hypotheses), "ids": [item.get("id") for item in hypotheses if item.get("id")]},
        ))

    coordination = topology.get("evidence_coordination") or {}
    conflicts = [key for key, value in coordination.items() if isinstance(value, dict) and value.get("conflict")]
    if conflicts:
        blockers.append(_blocker(
            "vlm_cv_conflict",
            "Local and cloud architectural evidence conflict.",
            details={"fields": conflicts},
        ))

    safety_status = solution.get("safety_status")
    solver_code = REVIEW_SOLVER_STATUSES.get(safety_status)
    if solver_code:
        blockers.append(_blocker(
            solver_code,
            "Constraint solver output requires explicit review.",
            details={"safety_status": safety_status, "reasons": solution.get("fallback_reasons") or []},
        ))

    hard_violations = solution.get("hard_violations") or []
    if hard_violations or solution.get("constraint_status") == "failed":
        blockers.append(_blocker(
            "hard_constraint_unsatisfied",
            "One or more hard dimensions could not be satisfied.",
            details={"constraint_ids": hard_violations},
        ))

    if ir:
        pipeline_stage = "ir_ready"
    elif solution:
        pipeline_stage = "solved"
    elif topology:
        pipeline_stage = "understood"
    else:
        pipeline_stage = "observed"

    blocker_codes = {item["code"] for item in blockers}
    if "metric_scale_missing" in blocker_codes:
        readiness = "needs_scale"
    elif blockers:
        readiness = "needs_review"
    else:
        readiness = "ready_to_generate"

    return {
        "readiness_version": "reconstruction-readiness-v1",
        "pipeline_stage": pipeline_stage,
        "readiness": readiness,
        "ready_to_generate": readiness == "ready_to_generate",
        "blockers": blockers,
    }
