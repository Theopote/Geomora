"""A3 Reconstruction Baseline Gate evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GateThresholds:
    val_window_recall_min: float = 0.80
    holdout_generate_min: int = 4
    holdout_generate_total: int = 5
    r0_mean_rqs_min: float = 45.0
    stage_a_mean_rqs_min: float = 70.0
    topology_storey_accuracy_min: float = 0.50
    geometry_normalized_mae_max: float = 0.25
    sketchup_pass_rate_min: float = 0.85
    rationalization_improvement_min: float = 0.10
    min_gt_review_rounds: int = 2
    solver_residual_reduction_min: float = 0.0
    solver_hard_satisfaction_min: float = 1.0
    solver_mean_bbox_drift_max: float = 0.03
    solver_max_bbox_drift_max: float = 0.10


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
    checks: list[GateCheck] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "passed": self.passed,
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
    rows = _collect_rows(minimal_set, results, truths=truths)
    report = A3GateReport(phase=phase, passed=True)

    evaluated = [row for row in rows if row.get("metrics")]
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

    val_rows = [row for row in evaluated if row.get("split") == "val"]
    holdout_rows = [row for row in evaluated if row.get("split") == "holdout"]

    val_recalls = [
        row["metrics"]["detection"]["window"]["recall"]
        for row in val_rows
        if row["metrics"].get("detection") and row["metrics"]["detection"].get("window")
    ]
    val_recall = _mean(val_recalls)
    val_passed = val_recall is not None and val_recall >= thresholds.val_window_recall_min
    report.checks.append(
        GateCheck(
            id="val_window_recall",
            passed=val_passed,
            actual=round(val_recall, 4) if val_recall is not None else None,
            threshold=thresholds.val_window_recall_min,
            detail="Validation split window recall",
        )
    )
    if not val_passed:
        report.passed = False

    rqss = [row["metrics"]["rqs"] for row in evaluated if row["metrics"].get("rqs") is not None]
    mean_rqs = _mean(rqss)
    rqs_threshold = thresholds.r0_mean_rqs_min if phase == "r0_objective" else thresholds.stage_a_mean_rqs_min
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

    coverages = [row["metrics"]["coverage"] for row in evaluated if row["metrics"].get("coverage") is not None]
    mean_coverage = _mean(coverages)
    required_coverage = 0.70 if phase == "r0_objective" else 0.90
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
    topology_passed = mean_storey_accuracy is not None and mean_storey_accuracy >= thresholds.topology_storey_accuracy_min
    report.checks.append(
        GateCheck(
            id="topology_storey_accuracy",
            passed=topology_passed,
            actual=round(mean_storey_accuracy, 4) if mean_storey_accuracy is not None else None,
            threshold=thresholds.topology_storey_accuracy_min,
            detail="Mean storey count accuracy",
        )
    )
    if not topology_passed:
        report.passed = False

    geometry_maes = [
        row["metrics"]["geometry"]["normalized_mae"]
        for row in evaluated
        if row["metrics"].get("geometry") and row["metrics"]["geometry"].get("normalized_mae") is not None
    ]
    mean_geometry_mae = _mean(geometry_maes)
    geometry_passed = mean_geometry_mae is not None and mean_geometry_mae <= thresholds.geometry_normalized_mae_max
    report.checks.append(
        GateCheck(
            id="geometry_normalized_mae",
            passed=geometry_passed,
            actual=round(mean_geometry_mae, 4) if mean_geometry_mae is not None else None,
            threshold=thresholds.geometry_normalized_mae_max,
            detail="Mean normalized geometry MAE (lower is better)",
        )
    )
    if not geometry_passed:
        report.passed = False

    sketchup_rows = [
        row
        for row in evaluated
        if row["metrics"].get("sketchup") and row["metrics"]["sketchup"].get("pass_rate") is not None
    ]
    if phase != "r0_objective":
        sketchup_rates = [row["metrics"]["sketchup"]["pass_rate"] for row in sketchup_rows]
        mean_sketchup = _mean(sketchup_rates)
        sketchup_passed = mean_sketchup is not None and mean_sketchup >= thresholds.sketchup_pass_rate_min
        report.checks.append(
            GateCheck(
                id="sketchup_pass_rate",
                passed=sketchup_passed,
                actual=round(mean_sketchup, 4) if mean_sketchup is not None else None,
                threshold=thresholds.sketchup_pass_rate_min,
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

    if phase == "r0_objective":
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
    if phase not in ("r0_objective",) and not holdout_passed:
        report.passed = False

    if phase != "r0_objective":
        solver_metrics = [row["metrics"].get("constraint_solver") for row in evaluated]
        solver_metrics = [item for item in solver_metrics if item is not None]
        if phase == "stage_a_full" and not solver_metrics:
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

    if truths and phase == "stage_a_full":
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
