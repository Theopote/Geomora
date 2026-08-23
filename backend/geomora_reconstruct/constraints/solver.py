"""Weighted projection solver for facade opening constraints v0.1."""
from __future__ import annotations

from copy import deepcopy
from statistics import mean
from typing import Any, Callable

SUPPORTED_TYPES = {"equal_width", "equal_height", "equal_spacing", "align", "vertical", "symmetry", "fixed_dimension"}


def _width(item: dict[str, Any]) -> float:
    return float(item["bbox"][2]) - float(item["bbox"][0])


def _height(item: dict[str, Any]) -> float:
    return float(item["bbox"][3]) - float(item["bbox"][1])


def _center_x(item: dict[str, Any]) -> float:
    return (float(item["bbox"][0]) + float(item["bbox"][2])) / 2.0


def _set_width(item: dict[str, Any], target: float, alpha: float) -> None:
    width = _width(item) + alpha * (target - _width(item))
    center = _center_x(item)
    item["bbox"][0], item["bbox"][2] = center - width / 2.0, center + width / 2.0


def _set_height(item: dict[str, Any], target: float, alpha: float) -> None:
    height = _height(item) + alpha * (target - _height(item))
    sill = float(item["bbox"][3])
    item["bbox"][1] = sill - height


def _set_sill(item: dict[str, Any], target: float, alpha: float) -> None:
    height = _height(item)
    sill = float(item["bbox"][3]) + alpha * (target - float(item["bbox"][3]))
    item["bbox"][1], item["bbox"][3] = sill - height, sill


def _set_center_x(item: dict[str, Any], target: float, alpha: float) -> None:
    width = _width(item)
    center = _center_x(item) + alpha * (target - _center_x(item))
    item["bbox"][0], item["bbox"][2] = center - width / 2.0, center + width / 2.0


def _mean_abs(values: list[float], target: float) -> float:
    return mean(abs(value - target) for value in values) if values else 0.0


def constraint_residual(constraint: dict[str, Any], targets: list[dict[str, Any]], *, facade_center: float = 0.5) -> float:
    kind = constraint.get("type")
    if len(targets) < 2 or kind == "fixed_dimension":
        return 0.0
    if kind == "equal_width":
        values = [_width(item) for item in targets]
        return _mean_abs(values, mean(values))
    if kind == "equal_height":
        values = [_height(item) for item in targets]
        return _mean_abs(values, mean(values))
    if kind == "align":
        values = [float(item["bbox"][3]) for item in targets]
        return _mean_abs(values, mean(values))
    if kind == "vertical":
        values = [_center_x(item) for item in targets]
        return _mean_abs(values, mean(values))
    ordered = sorted(targets, key=_center_x)
    centers = [_center_x(item) for item in ordered]
    if kind == "equal_spacing" and len(centers) >= 3:
        step = (centers[-1] - centers[0]) / (len(centers) - 1)
        return mean(abs(value - (centers[0] + index * step)) for index, value in enumerate(centers))
    if kind == "symmetry":
        pairs = [abs((centers[index] + centers[-index - 1]) / 2.0 - facade_center) for index in range(len(centers) // 2)]
        return mean(pairs) if pairs else abs(centers[0] - facade_center)
    return 0.0


def _project(constraint: dict[str, Any], targets: list[dict[str, Any]], alpha: float, facade_center: float) -> None:
    kind = constraint.get("type")
    if len(targets) < 2:
        return
    if kind == "equal_width":
        target = mean(_width(item) for item in targets)
        for item in targets:
            _set_width(item, target, alpha)
    elif kind == "equal_height":
        target = mean(_height(item) for item in targets)
        for item in targets:
            _set_height(item, target, alpha)
    elif kind == "align":
        target = mean(float(item["bbox"][3]) for item in targets)
        for item in targets:
            _set_sill(item, target, alpha)
    elif kind == "vertical":
        target = mean(_center_x(item) for item in targets)
        for item in targets:
            _set_center_x(item, target, alpha)
    elif kind == "equal_spacing" and len(targets) >= 3:
        ordered = sorted(targets, key=_center_x)
        left, right = _center_x(ordered[0]), _center_x(ordered[-1])
        step = (right - left) / (len(ordered) - 1)
        for index, item in enumerate(ordered):
            _set_center_x(item, left + index * step, alpha)
    elif kind == "symmetry":
        ordered = sorted(targets, key=_center_x)
        for index in range(len(ordered) // 2):
            left, right = ordered[index], ordered[-index - 1]
            half_span = (_center_x(right) - _center_x(left)) / 2.0
            _set_center_x(left, facade_center - half_span, alpha)
            _set_center_x(right, facade_center + half_span, alpha)


def _clamp_bbox(item: dict[str, Any], bounds: list[float]) -> None:
    fx1, fy1, fx2, fy2 = bounds
    x1, y1, x2, y2 = [float(value) for value in item["bbox"]]
    width, height = min(x2 - x1, fx2 - fx1), min(y2 - y1, fy2 - fy1)
    x1 = min(max(x1, fx1), fx2 - width)
    y1 = min(max(y1, fy1), fy2 - height)
    item["bbox"] = [x1, y1, x1 + width, y1 + height]


def solve_opening_constraints(
    openings: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    *,
    facade_bbox: list[float] | None = None,
    iterations: int = 8,
) -> dict[str, Any]:
    solved = deepcopy(openings)
    by_id = {str(item["id"]): item for item in solved if item.get("id")}
    bounds = facade_bbox or [0.0, 0.0, 1.0, 1.0]
    facade_center = (bounds[0] + bounds[2]) / 2.0
    active = [item for item in constraints if item.get("type") in SUPPORTED_TYPES and item.get("status", "proposed") in ("proposed", "accepted")]

    def targets_for(item: dict[str, Any]) -> list[dict[str, Any]]:
        return [by_id[target] for target in item.get("targets", []) if target in by_id]

    before = {item.get("id", f"constraint_{index}"): constraint_residual(item, targets_for(item), facade_center=facade_center) for index, item in enumerate(active)}
    ordered = sorted(active, key=lambda item: item.get("priority") == "hard")
    for _ in range(max(1, iterations)):
        for item in ordered:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 1.0))))
            weight = max(0.0, min(1.0, float(item.get("weight", confidence))))
            alpha = 1.0 if item.get("priority") == "hard" else max(0.05, min(0.8, confidence * weight * 0.5))
            _project(item, targets_for(item), alpha, facade_center)
        for opening in solved:
            _clamp_bbox(opening, bounds)

    for item in solved:
        if "observed_bbox" not in item:
            original = next((source for source in openings if source.get("id") == item.get("id")), None)
            item["observed_bbox"] = list((original or item)["bbox"])
        item["bbox"] = [round(value, 6) for value in item["bbox"]]

    reports = []
    hard_violations = []
    for index, item in enumerate(active):
        constraint_id = item.get("id", f"constraint_{index}")
        residual_after = constraint_residual(item, targets_for(item), facade_center=facade_center)
        report = {
            "id": constraint_id,
            "type": item.get("type"),
            "priority": item.get("priority", "soft"),
            "residual_before": round(before[constraint_id], 8),
            "residual_after": round(residual_after, 8),
            "satisfied": residual_after <= (1e-6 if item.get("priority") == "hard" else before[constraint_id] + 1e-9),
        }
        reports.append(report)
        if item.get("priority") == "hard" and not report["satisfied"]:
            hard_violations.append(constraint_id)
    return {
        "method": "weighted_projection_v0.1",
        "iterations": max(1, iterations),
        "openings": solved,
        "constraints": reports,
        "mean_residual_before": round(mean(before.values()), 8) if before else 0.0,
        "mean_residual_after": round(mean(item["residual_after"] for item in reports), 8) if reports else 0.0,
        "hard_violations": hard_violations,
    }


def solve_prediction_constraints(prediction: dict[str, Any], *, iterations: int = 8) -> dict[str, Any] | None:
    constraints = prediction.get("constraint_suggestions") or []
    openings = prediction.get("openings") or []
    if not constraints or not openings:
        return None
    topology = prediction.get("topology") or {}
    solution = solve_opening_constraints(openings, constraints, facade_bbox=topology.get("facade_bbox"), iterations=iterations)
    prediction["openings"] = solution.pop("openings")
    prediction["constraint_solution"] = solution
    return solution
