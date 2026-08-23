"""Integrity metrics for geometry changed by the constraint solver."""
from __future__ import annotations

from itertools import combinations
from statistics import mean
from typing import Any


def _valid_bbox(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 4 and all(isinstance(v, (int, float)) for v in value)


def _overlap_count(boxes: list[list[float]]) -> int:
    count = 0
    for left, right in combinations(boxes, 2):
        if min(left[2], right[2]) > max(left[0], right[0]) and min(left[3], right[3]) > max(left[1], right[1]):
            count += 1
    return count


def _outside_count(boxes: list[list[float]], facade: list[float]) -> int:
    fx1, fy1, fx2, fy2 = facade
    return sum(x1 < fx1 or y1 < fy1 or x2 > fx2 or y2 > fy2 or x2 <= x1 or y2 <= y1 for x1, y1, x2, y2 in boxes)


def evaluate_constraint_solver(prediction: dict[str, Any]) -> dict[str, Any] | None:
    """Measure solver improvement and ensure it did not damage observed geometry."""
    solution = prediction.get("constraint_solution")
    if not isinstance(solution, dict):
        return None

    constraints = solution.get("constraints") or []
    before = solution.get("mean_residual_before")
    after = solution.get("mean_residual_after")
    reduction = None
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        reduction = 1.0 if before == 0 and after == 0 else (before - after) / before if before > 0 else 0.0

    hard = [item for item in constraints if item.get("priority") == "hard"]
    hard_satisfied = sum(bool(item.get("satisfied")) for item in hard)
    hard_rate = hard_satisfied / len(hard) if hard else 1.0

    observed: list[list[float]] = []
    solved: list[list[float]] = []
    drift: list[float] = []
    coordinate_drift: list[float] = []
    for opening in prediction.get("openings") or []:
        old, new = opening.get("observed_bbox"), opening.get("bbox")
        if not (_valid_bbox(old) and _valid_bbox(new)):
            continue
        old_box, new_box = list(map(float, old)), list(map(float, new))
        observed.append(old_box)
        solved.append(new_box)
        deltas = [abs(a - b) for a, b in zip(old_box, new_box)]
        drift.append(mean(deltas))
        coordinate_drift.extend(deltas)

    facade = prediction.get("facade_bbox") or (prediction.get("topology") or {}).get("facade_bbox") or [0.0, 0.0, 1.0, 1.0]
    if not _valid_bbox(facade):
        facade = [0.0, 0.0, 1.0, 1.0]
    overlaps_before, overlaps_after = _overlap_count(observed), _overlap_count(solved)
    outside_before, outside_after = _outside_count(observed, list(map(float, facade))), _outside_count(solved, list(map(float, facade)))

    return {
        "constraint_count": len(constraints),
        "soft_constraint_count": len(constraints) - len(hard),
        "hard_constraint_count": len(hard),
        "mean_residual_before": before,
        "mean_residual_after": after,
        "residual_reduction": round(reduction, 6) if reduction is not None else None,
        "hard_satisfaction_rate": round(hard_rate, 6),
        "hard_violations": len(hard) - hard_satisfied,
        "compared_openings": len(solved),
        "mean_bbox_drift": round(mean(drift), 6) if drift else None,
        "max_bbox_drift": round(max(coordinate_drift), 6) if coordinate_drift else None,
        "overlaps_before": overlaps_before,
        "overlaps_after": overlaps_after,
        "introduced_overlaps": max(0, overlaps_after - overlaps_before),
        "boundary_violations_before": outside_before,
        "boundary_violations_after": outside_after,
        "introduced_boundary_violations": max(0, outside_after - outside_before),
    }
