"""Tiered Reconstruction Core gate evaluation (RC-G0/RC-G1/RC-G2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .gt_validator import validate_ground_truth


@dataclass(frozen=True)
class GateThresholds:
    holdout_generate_min: int = 4
    holdout_generate_total: int = 5
    min_gt_review_rounds: int = 2
    solver_residual_reduction_min: float = 0.0
    solver_hard_satisfaction_min: float = 1.0
    solver_mean_bbox_drift_max: float = 0.03
    solver_max_bbox_drift_max: float = 0.10


@dataclass(frozen=True)
class GateProfile:
    id: str
    maturity_claim: str
    min_photos: int
    min_holdout_photos: int
    mean_rqs_min: float
    per_photo_rqs_min: float
    coverage_min: float
    window_recall_min: float
    window_precision_min: float | None
    storey_accuracy_min: float
    exact_storey_min: float | None
    bay_accuracy_min: float | None
    storey_assignment_min: float | None
    bay_assignment_min: float | None
    geometry_mae_max: float
    per_photo_geometry_mae_max: float | None
    sketchup_pass_rate_min: float | None


GATE_PROFILES = {
    "RC-G0": GateProfile("RC-G0", "prototype_bootstrap", 1, 0, 45.0, 0.0, 0.70, 0.80, None, 0.50, None, None, None, None, 0.25, None, None),
    "RC-G1": GateProfile("RC-G1", "reconstruction_alpha", 5, 5, 70.0, 50.0, 0.90, 0.85, 0.85, 0.85, 0.80, 0.75, 0.80, 0.75, 0.12, 0.20, 0.90),
    "RC-G2": GateProfile("RC-G2", "product_beta", 20, 5, 82.0, 65.0, 0.95, 0.92, 0.92, 0.95, 0.92, 0.88, 0.90, 0.88, 0.07, 0.12, 0.95),
}


def resolve_gate_profile(phase: str) -> GateProfile:
    aliases = {
        "r0_objective": "RC-G0", "prototype_bootstrap": "RC-G0", "rc_g0": "RC-G0",
        "stage_a_core": "RC-G1", "stage_a_full": "RC-G1", "reconstruction_alpha": "RC-G1", "rc_g1": "RC-G1",
        "product_beta": "RC-G2", "rc_g2": "RC-G2",
    }
    try:
        return GATE_PROFILES[aliases[phase.lower()]]
    except KeyError as error:
        raise ValueError(f"unknown gate phase: {phase}") from error


@dataclass
class GateCheck:
    id: str
    passed: bool
    actual: Any
    threshold: Any
    detail: str


@dataclass
class A3GateReport:
    phase: str
    passed: bool
    gate: str = "RC-G0"
    maturity_claim: str = "prototype_bootstrap"
    checks: list[GateCheck] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        gate_order = ("RC-G0", "RC-G1", "RC-G2")
        higher_gates = list(gate_order[gate_order.index(self.gate) + 1 :])
        return {
            "phase": self.phase,
            "gate": self.gate,
            "maturity_claim": self.maturity_claim,
            "passed": self.passed,
            "product_ready": self.passed and self.gate == "RC-G2",
            "higher_gates_not_evaluated": higher_gates,
            "user_facing_claim_allowed": (
                "Product Beta benchmark criteria passed" if self.passed and self.gate == "RC-G2" else
                "Reconstruction Alpha benchmark criteria passed" if self.passed and self.gate == "RC-G1" else
                "Pipeline and measurement bootstrap verified" if self.passed else "No readiness claim allowed"
            ),
            "checks": [
                {
                    "id": check.id,
                    "passed": check.passed,
                    "actual": check.actual,
                    "threshold": check.threshold,
                    "detail": check.detail,
                }
                for check in self.checks
            ],
            "blockers": self.blockers,
            "summary": self.summary,
        }


def _split_map(minimal_set: dict[str, Any]) -> dict[str, str]:
    return {item["id"]: item.get("split", "unknown") for item in minimal_set.get("photos", [])}


def _gt_reviewed(truth: dict[str, Any], *, min_rounds: int) -> bool:
    status = truth.get("annotation_status", "")
    rounds = int(truth.get("review_rounds", 0) or 0)
    return status == "reviewed_v1" and rounds >= min_rounds


def _metric_anchor_ready(truth: dict[str, Any]) -> bool:
    if truth.get("metric"):
        return True
    anchors = truth.get("metric_anchors") or []
    if not anchors:
        return True
    return all(anchor.get("distance_mm") not in (None, "") for anchor in anchors)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _collect_rows(
    minimal_set: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    truths: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    split_by_id = _split_map(minimal_set)
    rows = []
    for row in results:
        photo_id = row["photo_id"]
        metrics = row.get("metrics")
        if metrics is None:
            rows.append({"photo_id": photo_id, "split": split_by_id.get(photo_id), "metrics": None})
            continue
        enriched = {
            "photo_id": photo_id,
            "split": split_by_id.get(photo_id),
            "metrics": metrics,
        }
        if truths and photo_id in truths:
            enriched["truth"] = truths[photo_id]
        rows.append(enriched)
    return rows


def evaluate_a3_gate(
    minimal_set: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    truths: dict[str, dict[str, Any]] | None = None,
    phase: str = "r0_objective",
    thresholds: GateThresholds | None = None,
) -> A3GateReport:
    thresholds = thresholds or GateThresholds()
    profile = resolve_gate_profile(phase)
    rows = _collect_rows(minimal_set, results, truths=truths)
    report = A3GateReport(phase=phase, passed=True, gate=profile.id, maturity_claim=profile.maturity_claim)

    evaluated = [row for row in rows if row.get("metrics")]
    sample_count_passed = len(evaluated) >= profile.min_photos
    report.checks.append(GateCheck("minimum_sample_count", sample_count_passed, len(evaluated), profile.min_photos, "Minimum evaluated photos for this maturity claim"))
    if not sample_count_passed:
        report.passed = False
    if len(evaluated) != len(rows):
        missing = [row["photo_id"] for row in rows if not row.get("metrics")]
        report.blockers.append(f"missing_metrics:{','.join(missing)}")
        report.passed = False

    if truths:
        for row in rows:
            truth = truths.get(row["photo_id"])
            if truth is None:
                report.blockers.append(f"missing_ground_truth:{row['photo_id']}")
                report.passed = False
                continue
            if not _gt_reviewed(truth, min_rounds=thresholds.min_gt_review_rounds):
                report.blockers.append(f"ground_truth_not_reviewed:{row['photo_id']}")
                report.passed = False
            audit = validate_ground_truth(truth)
            if not audit.gate_ready:
                codes = ",".join(sorted({issue.code for issue in audit.issues}))
                report.blockers.append(f"ground_truth_inconsistent:{row['photo_id']}:{codes}")
                report.passed = False
                report.checks.append(
                    GateCheck(
                        id=f"ground_truth_consistency:{row['photo_id']}",
                        passed=False,
                        actual={"errors": len(audit.errors), "warnings": len(audit.warnings)},
                        threshold={"errors": 0, "warnings": 0},
                        detail="Ground truth must pass structural and spatial consistency audit",
                    )
                )

    val_rows = [row for row in evaluated if row.get("split") == "val"]
    holdout_rows = [row for row in evaluated if row.get("split") == "holdout"]
    holdout_count_passed = len(holdout_rows) >= profile.min_holdout_photos
    report.checks.append(GateCheck("minimum_holdout_count", holdout_count_passed, len(holdout_rows), profile.min_holdout_photos, "Minimum untouched hold-out photos"))
    if not holdout_count_passed:
        report.passed = False

    val_recalls = [
        row["metrics"]["detection"]["window"]["recall"]
        for row in val_rows
        if row["metrics"].get("detection") and row["metrics"]["detection"].get("window")
    ]
    val_recall = _mean(val_recalls)
    val_passed = val_recall is not None and val_recall >= profile.window_recall_min
    report.checks.append(
        GateCheck(
            id="val_window_recall",
            passed=val_passed,
            actual=round(val_recall, 4) if val_recall is not None else None,
            threshold=profile.window_recall_min,
            detail="Validation split window recall",
        )
    )
    if not val_passed:
        report.passed = False

    if profile.window_precision_min is not None:
        val_precisions = [
            row["metrics"]["detection"]["window"]["precision"]
            for row in val_rows
            if row["metrics"].get("detection") and row["metrics"]["detection"].get("window")
            and row["metrics"]["detection"]["window"].get("precision") is not None
        ]
        mean_precision = _mean(val_precisions)
        precision_passed = mean_precision is not None and mean_precision >= profile.window_precision_min
        report.checks.append(GateCheck("val_window_precision", precision_passed, round(mean_precision, 4) if mean_precision is not None else None, profile.window_precision_min, "Validation split window precision"))
        if not precision_passed:
            report.passed = False

    rqss = [row["metrics"]["rqs"] for row in evaluated if row["metrics"].get("rqs") is not None]
    mean_rqs = _mean(rqss)
    rqs_threshold = profile.mean_rqs_min
    rqs_passed = mean_rqs is not None and mean_rqs >= rqs_threshold
    report.checks.append(
        GateCheck(
            id="mean_rqs",
            passed=rqs_passed,
            actual=mean_rqs,
            threshold=rqs_threshold,
            detail="Mean RQS over evaluated metric groups",
        )
    )
    if not rqs_passed:
        report.passed = False

    if profile.per_photo_rqs_min > 0:
        lowest_rqs = min(rqss) if rqss else None
        per_photo_rqs_passed = lowest_rqs is not None and lowest_rqs >= profile.per_photo_rqs_min
        report.checks.append(GateCheck("per_photo_rqs_floor", per_photo_rqs_passed, lowest_rqs, profile.per_photo_rqs_min, "Lowest per-photo RQS"))
        if not per_photo_rqs_passed:
            report.passed = False

    coverages = [row["metrics"]["coverage"] for row in evaluated if row["metrics"].get("coverage") is not None]
    mean_coverage = _mean(coverages)
    required_coverage = profile.coverage_min
    coverage_passed = mean_coverage is not None and mean_coverage >= required_coverage
    report.checks.append(
        GateCheck(
            id="mean_coverage",
            passed=coverage_passed,
            actual=round(mean_coverage, 4) if mean_coverage is not None else None,
            threshold=required_coverage,
            detail="Mean annotation coverage across metric groups",
        )
    )
    if not coverage_passed:
        report.passed = False

    storey_accuracies = [
        row["metrics"]["topology"]["storey_accuracy"]
        for row in evaluated
        if row["metrics"].get("topology") and row["metrics"]["topology"].get("storey_accuracy") is not None
    ]
    mean_storey_accuracy = _mean(storey_accuracies)
    topology_passed = mean_storey_accuracy is not None and mean_storey_accuracy >= profile.storey_accuracy_min
    report.checks.append(
        GateCheck(
            id="topology_storey_accuracy",
            passed=topology_passed,
            actual=round(mean_storey_accuracy, 4) if mean_storey_accuracy is not None else None,
            threshold=profile.storey_accuracy_min,
            detail="Mean storey count accuracy",
        )
    )
    if not topology_passed:
        report.passed = False

    if profile.exact_storey_min is not None:
        topology_metrics = [row["metrics"].get("topology") or {} for row in evaluated]
        exact_values = [item.get("storey_exact") for item in topology_metrics if item.get("storey_exact") is not None]
        bay_values = [item.get("bay_accuracy") for item in topology_metrics if item.get("bay_accuracy") is not None]
        storey_assignments = [item.get("window_to_storey_assignment_accuracy") for item in topology_metrics if item.get("window_to_storey_assignment_accuracy") is not None]
        bay_assignments = [item.get("window_to_bay_assignment_accuracy") for item in topology_metrics if item.get("window_to_bay_assignment_accuracy") is not None]
        topology_checks = [
            GateCheck("topology_exact_storey", (_mean(exact_values) or 0.0) >= profile.exact_storey_min, round(_mean(exact_values), 4) if exact_values else None, profile.exact_storey_min, "Exact storey-count accuracy"),
            GateCheck("topology_bay_accuracy", (_mean(bay_values) or 0.0) >= profile.bay_accuracy_min, round(_mean(bay_values), 4) if bay_values else None, profile.bay_accuracy_min, "Mean bay-count accuracy"),
            GateCheck("topology_storey_assignment", (_mean(storey_assignments) or 0.0) >= profile.storey_assignment_min, round(_mean(storey_assignments), 4) if storey_assignments else None, profile.storey_assignment_min, "Window-to-storey assignment accuracy"),
            GateCheck("topology_bay_assignment", (_mean(bay_assignments) or 0.0) >= profile.bay_assignment_min, round(_mean(bay_assignments), 4) if bay_assignments else None, profile.bay_assignment_min, "Window-to-bay assignment accuracy"),
        ]
        report.checks.extend(topology_checks)
        if not all(check.passed for check in topology_checks):
            report.passed = False

    geometry_maes = [
        row["metrics"]["geometry"]["normalized_mae"]
        for row in evaluated
        if row["metrics"].get("geometry") and row["metrics"]["geometry"].get("normalized_mae") is not None
    ]
    mean_geometry_mae = _mean(geometry_maes)
    geometry_passed = mean_geometry_mae is not None and mean_geometry_mae <= profile.geometry_mae_max
    report.checks.append(
        GateCheck(
            id="geometry_normalized_mae",
            passed=geometry_passed,
            actual=round(mean_geometry_mae, 4) if mean_geometry_mae is not None else None,
            threshold=profile.geometry_mae_max,
            detail="Mean normalized geometry MAE (lower is better)",
        )
    )
    if not geometry_passed:
        report.passed = False

    if profile.per_photo_geometry_mae_max is not None:
        worst_geometry_mae = max(geometry_maes) if geometry_maes else None
        per_photo_geometry_passed = worst_geometry_mae is not None and worst_geometry_mae <= profile.per_photo_geometry_mae_max
        report.checks.append(GateCheck("per_photo_geometry_mae", per_photo_geometry_passed, worst_geometry_mae, profile.per_photo_geometry_mae_max, "Worst per-photo normalized geometry MAE"))
        catastrophic = sum(
            1 for row in evaluated
            if (row["metrics"].get("topology") or {}).get("storey_accuracy", 0.0) < 0.50
            or (
                (row["metrics"].get("geometry") or {}).get("normalized_mae")
                if (row["metrics"].get("geometry") or {}).get("normalized_mae") is not None
                else 1.0
            ) > profile.per_photo_geometry_mae_max
        )
        report.checks.append(GateCheck("catastrophic_failure_count", catastrophic == 0, catastrophic, 0, "Photos with severe topology or geometry failure"))
        if not per_photo_geometry_passed or catastrophic:
            report.passed = False

    sketchup_rows = [
        row
        for row in evaluated
        if row["metrics"].get("sketchup") and row["metrics"]["sketchup"].get("pass_rate") is not None
    ]
    if profile.id != "RC-G0":
        sketchup_rates = [row["metrics"]["sketchup"]["pass_rate"] for row in sketchup_rows]
        mean_sketchup = _mean(sketchup_rates)
        sketchup_passed = mean_sketchup is not None and mean_sketchup >= profile.sketchup_pass_rate_min
        report.checks.append(
            GateCheck(
                id="sketchup_pass_rate",
                passed=sketchup_passed,
                actual=round(mean_sketchup, 4) if mean_sketchup is not None else None,
                threshold=profile.sketchup_pass_rate_min,
                detail="Mean heuristic SketchUp readiness pass rate",
            )
        )
        if not sketchup_passed:
            report.passed = False

    generate_stable_count = 0
    for row in holdout_rows:
        sketchup = row["metrics"].get("sketchup")
        if sketchup and sketchup.get("generate_stable"):
            generate_stable_count += 1

    if holdout_rows:
        if len(holdout_rows) < thresholds.holdout_generate_total:
            holdout_required = max(
                1,
                round(thresholds.holdout_generate_min * len(holdout_rows) / thresholds.holdout_generate_total),
            )
        else:
            holdout_required = thresholds.holdout_generate_min
        holdout_passed = generate_stable_count >= holdout_required
        holdout_threshold = f">={holdout_required}/{len(holdout_rows)}"
    else:
        holdout_passed = True
        holdout_threshold = "n/a"
        holdout_required = 0

    if profile.id == "RC-G0":
        holdout_passed = True

    report.checks.append(
        GateCheck(
            id="holdout_generate_stable",
            passed=holdout_passed,
            actual=f"{generate_stable_count}/{len(holdout_rows)}",
            threshold=holdout_threshold,
            detail="Hold-out photos with heuristic generate_stable check",
        )
    )
    if profile.id != "RC-G0" and not holdout_passed:
        report.passed = False

    if profile.id != "RC-G0":
        solver_metrics = [row["metrics"].get("constraint_solver") for row in evaluated]
        solver_metrics = [item for item in solver_metrics if item is not None]
        if not solver_metrics:
            report.blockers.append("missing_constraint_solver_metrics")
            report.passed = False
        if solver_metrics:
            reductions = [item["residual_reduction"] for item in solver_metrics if item.get("residual_reduction") is not None]
            mean_reduction = _mean(reductions)
            hard_rate = min(item.get("hard_satisfaction_rate", 0.0) for item in solver_metrics)
            mean_drift = max((item.get("mean_bbox_drift") or 0.0) for item in solver_metrics)
            max_drift = max((item.get("max_bbox_drift") or 0.0) for item in solver_metrics)
            introduced = sum(item.get("introduced_overlaps", 0) + item.get("introduced_boundary_violations", 0) for item in solver_metrics)
            solver_checks = [
                GateCheck("solver_residual_reduction", mean_reduction is not None and mean_reduction >= thresholds.solver_residual_reduction_min, round(mean_reduction, 4) if mean_reduction is not None else None, thresholds.solver_residual_reduction_min, "Mean relative constraint residual reduction"),
                GateCheck("solver_hard_satisfaction", hard_rate >= thresholds.solver_hard_satisfaction_min, hard_rate, thresholds.solver_hard_satisfaction_min, "Minimum hard-constraint satisfaction rate"),
                GateCheck("solver_geometry_drift", mean_drift <= thresholds.solver_mean_bbox_drift_max and max_drift <= thresholds.solver_max_bbox_drift_max, {"mean_max": mean_drift, "coordinate_max": max_drift}, {"mean_max": thresholds.solver_mean_bbox_drift_max, "coordinate_max": thresholds.solver_max_bbox_drift_max}, "Maximum drift from observed opening boxes"),
                GateCheck("solver_introduced_violations", introduced == 0, introduced, 0, "New overlap or facade-boundary violations"),
            ]
            report.checks.extend(solver_checks)
            if not all(check.passed for check in solver_checks):
                report.passed = False

    if truths and profile.id != "RC-G0":
        pending_anchors = [
            photo_id
            for photo_id, truth in truths.items()
            if photo_id in {row["photo_id"] for row in rows}
            and not _metric_anchor_ready(truth)
        ]
        anchors_passed = not pending_anchors
        report.checks.append(
            GateCheck(
                id="metric_anchors_reviewed",
                passed=anchors_passed,
                actual=pending_anchors or "ready",
                threshold="all anchors surveyed",
                detail="Measured metric anchors required for scale evaluation",
            )
        )
        if not anchors_passed:
            report.blockers.append(f"pending_metric_anchors:{','.join(pending_anchors)}")
            report.passed = False

    report.summary = {
        "photos": len(rows),
        "evaluated": len(evaluated),
        "mean_rqs": round(mean_rqs, 1) if mean_rqs is not None else None,
        "mean_coverage": round(mean_coverage, 4) if mean_coverage is not None else None,
        "val_window_recall": round(val_recall, 4) if val_recall is not None else None,
        "holdout_generate_stable": generate_stable_count,
        "solver_evaluated": sum(1 for row in evaluated if row["metrics"].get("constraint_solver") is not None),
    }
    return report


# Canonical name; the legacy function remains for stored scripts and reports.
evaluate_reconstruction_gate = evaluate_a3_gate
ReconstructionGateReport = A3GateReport
