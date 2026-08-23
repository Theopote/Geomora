"""Weighted projection solver for facade opening constraints v0.1."""
from __future__ import annotations

from copy import deepcopy
from statistics import mean
from typing import Any, Callable

from ..metric_anchors import anchor_axis, anchor_has_distance, derive_metric_from_anchors

SUPPORTED_TYPES = {"equal_width", "equal_height", "equal_spacing", "align", "vertical", "symmetry", "fixed_dimension"}
SAFETY_SOFT_WEIGHT_SCALES = (1.0, 0.25, 0.05)
UNRESOLVABLE_RESIDUAL = 1_000_000_000.0


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


def _fixed_property(constraint: dict[str, Any]) -> str:
    evidence = constraint.get("evidence") or {}
    return str(constraint.get("property") or evidence.get("property") or evidence.get("axis") or "").lower()


def _fixed_distance(constraint: dict[str, Any]) -> float | None:
    evidence = constraint.get("evidence") or {}
    value = constraint.get("distance_mm", evidence.get("distance_mm"))
    try: return float(value) if value is not None else None
    except (TypeError, ValueError): return None


def _fixed_target_normalized(constraint: dict[str, Any], metric: dict[str, float], bounds: list[float]) -> float | None:
    evidence = constraint.get("evidence") or {}
    if evidence.get("value_normalized") is not None:
        return float(evidence["value_normalized"])
    distance = _fixed_distance(constraint); prop = _fixed_property(constraint)
    if distance is None: return None
    if prop in {"width", "opening_width", "bay_pitch", "horizontal"}:
        facade = metric.get("facade_width_mm")
    elif prop in {"height", "opening_height", "sill", "sill_height", "storey_height", "vertical"}:
        facade = metric.get("facade_height_mm")
    else:
        return None
    return distance / facade if facade and facade > 0 else None


def constraint_residual(constraint: dict[str, Any], targets: list[dict[str, Any]], *, facade_center: float = 0.5, metric: dict[str, float] | None = None, bounds: list[float] | None = None) -> float:
    kind = constraint.get("type")
    metric = metric or {}; bounds = bounds or [0.0, 0.0, 1.0, 1.0]
    if kind == "fixed_dimension":
        prop = _fixed_property(constraint); distance = _fixed_distance(constraint)
        if prop in {"facade_width", "facade.width"}:
            return abs(float(metric["facade_width_mm"]) - distance) if distance is not None and metric.get("facade_width_mm") is not None else UNRESOLVABLE_RESIDUAL
        if prop in {"facade_height", "facade.height"}:
            return abs(float(metric["facade_height_mm"]) - distance) if distance is not None and metric.get("facade_height_mm") is not None else UNRESOLVABLE_RESIDUAL
        desired = _fixed_target_normalized(constraint, metric, bounds)
        if desired is None: return UNRESOLVABLE_RESIDUAL
        if prop == "bay_pitch":
            if len(targets) < 2: return UNRESOLVABLE_RESIDUAL
            centers = sorted(_center_x(item) for item in targets)
            return _mean_abs([centers[i+1]-centers[i] for i in range(len(centers)-1)], desired)
        if not targets: return UNRESOLVABLE_RESIDUAL
        if prop in {"width", "opening_width", "horizontal"}: values=[_width(item) for item in targets]
        elif prop in {"height", "opening_height", "storey_height", "vertical"}: values=[_height(item) for item in targets]
        elif prop in {"sill", "sill_height"}: values=[bounds[3]-float(item["bbox"][3]) for item in targets]
        else: return UNRESOLVABLE_RESIDUAL
        return _mean_abs(values, desired)
    if len(targets) < 2:
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


def _project(constraint: dict[str, Any], targets: list[dict[str, Any]], alpha: float, facade_center: float, metric: dict[str, float], bounds: list[float]) -> None:
    kind = constraint.get("type")
    if kind == "fixed_dimension":
        prop = _fixed_property(constraint); distance = _fixed_distance(constraint)
        if prop in {"facade_width", "facade.width"} and distance is not None:
            metric["facade_width_mm"] = distance
            return
        if prop in {"facade_height", "facade.height"} and distance is not None:
            metric["facade_height_mm"] = distance
            return
        desired = _fixed_target_normalized(constraint, metric, bounds)
        if desired is None: return
        if prop == "bay_pitch" and len(targets) >= 2:
            ordered=sorted(targets,key=_center_x); center=mean(_center_x(item) for item in ordered); start=center-desired*(len(ordered)-1)/2
            for index,item in enumerate(ordered): _set_center_x(item,start+index*desired,alpha)
        elif prop in {"width", "opening_width", "horizontal"}:
            for item in targets: _set_width(item,desired,alpha)
        elif prop in {"height", "opening_height", "storey_height", "vertical"}:
            for item in targets: _set_height(item,desired,alpha)
        elif prop in {"sill", "sill_height"}:
            for item in targets: _set_sill(item,bounds[3]-desired,alpha)
        return
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
    soft_weight_scale: float = 1.0,
    metric: dict[str, float] | None = None,
) -> dict[str, Any]:
    solved = deepcopy(openings)
    by_id = {str(item["id"]): item for item in solved if item.get("id")}
    bounds = facade_bbox or [0.0, 0.0, 1.0, 1.0]
    solved_metric = {key: float(value) for key, value in (metric or {}).items()}
    facade_center = (bounds[0] + bounds[2]) / 2.0
    active = [item for item in constraints if item.get("type") in SUPPORTED_TYPES and item.get("status", "proposed") in ("proposed", "accepted")]

    def targets_for(item: dict[str, Any]) -> list[dict[str, Any]]:
        return [by_id[target] for target in item.get("targets", []) if target in by_id]

    before = {item.get("id", f"constraint_{index}"): constraint_residual(item, targets_for(item), facade_center=facade_center, metric=solved_metric, bounds=bounds) for index, item in enumerate(active)}
    ordered = sorted(active, key=lambda item: item.get("priority") == "hard")
    for _ in range(max(1, iterations)):
        for item in ordered:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 1.0))))
            weight = max(0.0, min(1.0, float(item.get("weight", confidence))))
            alpha = 1.0 if item.get("priority") == "hard" else max(0.0, min(0.8, confidence * weight * 0.5 * soft_weight_scale))
            _project(item, targets_for(item), alpha, facade_center, solved_metric, bounds)
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
        residual_after = constraint_residual(item, targets_for(item), facade_center=facade_center, metric=solved_metric, bounds=bounds)
        report = {
            "id": constraint_id,
            "type": item.get("type"),
            "priority": item.get("priority", "soft"),
            "residual_before": round(before[constraint_id], 8),
            "residual_after": round(residual_after, 8),
            "satisfied": residual_after <= (1e-6 if item.get("priority") == "hard" else before[constraint_id] + 1e-9),
        }
        if item.get("type") == "fixed_dimension":
            report["property"] = _fixed_property(item)
            report["distance_mm"] = _fixed_distance(item)
        reports.append(report)
        if item.get("priority") == "hard" and not report["satisfied"]:
            hard_violations.append(constraint_id)
    return {
        "method": "weighted_projection_v0.2",
        "iterations": max(1, iterations),
        "openings": solved,
        "constraints": reports,
        "mean_residual_before": round(mean(before.values()), 8) if before else 0.0,
        "mean_residual_after": round(mean(item["residual_after"] for item in reports), 8) if reports else 0.0,
        "hard_violations": hard_violations,
        "soft_weight_scale": soft_weight_scale,
        "metric": solved_metric,
    }


def _overlaps(left: list[float], right: list[float]) -> bool:
    return min(left[2], right[2]) > max(left[0], right[0]) and min(left[3], right[3]) > max(left[1], right[1])


def _geometry_violations(openings: list[dict[str, Any]], bounds: list[float]) -> tuple[int, int]:
    boxes = [[float(value) for value in item["bbox"]] for item in openings]
    overlaps = sum(_overlaps(left, right) for index, left in enumerate(boxes) for right in boxes[index + 1 :])
    fx1, fy1, fx2, fy2 = bounds
    outside = sum(x1 < fx1 or y1 < fy1 or x2 > fx2 or y2 > fy2 or x2 <= x1 or y2 <= y1 for x1, y1, x2, y2 in boxes)
    return overlaps, outside


def _solution_safety(
    original: list[dict[str, Any]],
    solution: dict[str, Any],
    bounds: list[float],
    *,
    mean_drift_max: float = 0.03,
    coordinate_drift_max: float = 0.10,
) -> dict[str, Any]:
    solved = solution["openings"]
    by_id = {str(item.get("id")): item for item in original}
    deltas = [
        abs(float(value) - float(observed))
        for item in solved
        if str(item.get("id")) in by_id
        for value, observed in zip(item["bbox"], by_id[str(item.get("id"))]["bbox"])
    ]
    before_overlap, before_outside = _geometry_violations(original, bounds)
    after_overlap, after_outside = _geometry_violations(solved, bounds)
    mean_drift = mean(deltas) if deltas else 0.0
    max_drift = max(deltas, default=0.0)
    residual_safe = solution["mean_residual_after"] <= solution["mean_residual_before"] + 1e-9
    reasons = []
    if solution["hard_violations"]:
        reasons.append("hard_constraint_violation")
    if not residual_safe:
        reasons.append("residual_regression")
    if mean_drift > mean_drift_max or max_drift > coordinate_drift_max:
        reasons.append("excessive_geometry_drift")
    if after_overlap > before_overlap:
        reasons.append("introduced_overlap")
    if after_outside > before_outside:
        reasons.append("introduced_boundary_violation")
    return {
        "safe": not reasons,
        "reasons": reasons,
        "mean_bbox_drift": round(mean_drift, 6),
        "max_bbox_drift": round(max_drift, 6),
        "introduced_overlaps": max(0, after_overlap - before_overlap),
        "introduced_boundary_violations": max(0, after_outside - before_outside),
    }


def fixed_constraints_from_anchors(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    constraints = []
    for anchor in anchors:
        if not anchor_has_distance(anchor): continue
        anchor_type=str(anchor.get("type") or "user_distance"); prop=str(anchor.get("property") or "")
        if anchor_type == "facade_width": prop="facade_width"
        elif anchor_type == "facade_height": prop="facade_height"
        elif anchor_type == "opening_width": prop="width"
        elif anchor_type == "opening_height": prop="height"
        elif anchor_type in {"storey_height","bay_pitch"}: prop=anchor_type
        elif anchor_type == "user_distance": prop="facade_width" if anchor_axis(anchor)=="horizontal" else "facade_height"
        target=anchor.get("target"); targets=target if isinstance(target,list) else ([target] if target and target!="facade" else [])
        constraints.append({
            "id": f"fixed_{anchor.get('id','anchor')}", "type": "fixed_dimension", "targets": targets,
            "priority": "hard", "confidence": 1.0, "weight": 1.0, "status": "accepted", "source": "metric_anchor",
            "evidence": {"anchor_id": anchor.get("id"), "property": prop, "distance_mm": float(anchor["distance_mm"]), "target": target},
        })
    return constraints


def _prediction_metric(prediction: dict[str, Any], bounds: list[float]) -> dict[str, float]:
    metric = {key: float(value) for key,value in (prediction.get("metric") or {}).items()}
    hint = prediction.get("pipeline",{}).get("scale_hint") or {}
    if not metric.get("facade_width_mm") and hint.get("wall_length_mm"): metric["facade_width_mm"]=float(hint["wall_length_mm"])
    if not metric.get("facade_height_mm") and hint.get("wall_height_mm"): metric["facade_height_mm"]=float(hint["wall_height_mm"])
    anchored=derive_metric_from_anchors(prediction.get("metric_anchors") or [],topology=prediction.get("topology") or {},facade_bbox=bounds) or {}
    metric.update(anchored)
    return metric


def solve_prediction_constraints(prediction: dict[str, Any], *, iterations: int = 8) -> dict[str, Any] | None:
    constraints = list(prediction.get("constraint_suggestions") or [])
    existing_ids={item.get("id") for item in constraints}
    constraints.extend(item for item in fixed_constraints_from_anchors(prediction.get("metric_anchors") or []) if item.get("id") not in existing_ids)
    openings = prediction.get("openings") or []
    if not constraints:
        return None
    topology = prediction.get("topology") or {}
    bounds = topology.get("facade_bbox") or [0.0, 0.0, 1.0, 1.0]
    metric = _prediction_metric(prediction,bounds)
    attempts = []
    solution = None
    for scale in SAFETY_SOFT_WEIGHT_SCALES:
        candidate = solve_opening_constraints(openings, constraints, facade_bbox=bounds, iterations=iterations, soft_weight_scale=scale,metric=metric)
        safety = _solution_safety(openings, candidate, bounds)
        attempts.append({"soft_weight_scale": scale, **safety})
        if safety["safe"]:
            solution = candidate
            break
    if solution is None:
        solution = solve_opening_constraints(openings, constraints, facade_bbox=bounds, iterations=iterations, soft_weight_scale=0.0,metric=metric)
        solution["openings"] = deepcopy(openings)
        solution["metric"] = deepcopy(metric)
        for item in solution["openings"]:
            item.setdefault("observed_bbox", list(item["bbox"]))
        solution["mean_residual_after"] = solution["mean_residual_before"]
        solution["hard_violations"] = []
        for report in solution["constraints"]:
            report["residual_after"] = report["residual_before"]
            report["satisfied"] = report["residual_before"] <= (1e-6 if report["priority"] == "hard" else report["residual_before"] + 1e-9)
            if report["priority"] == "hard" and not report["satisfied"]:
                solution["hard_violations"].append(report["id"])
        solution["safety_status"] = "fallback_observed_geometry"
        solution["constraint_status"] = "failed" if solution["hard_violations"] else "fallback"
        solution["fallback_reasons"] = sorted({reason for attempt in attempts for reason in attempt["reasons"]})
    else:
        solution["safety_status"] = "accepted" if len(attempts) == 1 else "accepted_after_soft_weight_retry"
        solution["constraint_status"] = "satisfied"
    solution["safety_attempts"] = attempts
    prediction["openings"] = solution.pop("openings")
    solved_metric=solution.pop("metric",{})
    if solved_metric:
        prediction["metric"] = solved_metric
        prediction["metric_source"] = "constraint_solver"
    prediction["constraint_solution"] = solution
    return solution
