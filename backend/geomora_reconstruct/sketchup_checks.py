"""Heuristic SketchUp readiness checks from prediction + IR export."""
from __future__ import annotations

from typing import Any

from .ir_export import prediction_to_ir


def _opening_overlap(opening_a: dict[str, Any], opening_b: dict[str, Any]) -> bool:
    ax1, ay1, ax2, ay2 = opening_a["bbox"]
    bx1, by1, bx2, by2 = opening_b["bbox"]
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


def _openings_within_facade(openings: list[dict[str, Any]], facade_bbox: list[float] | None) -> bool:
    if not facade_bbox or len(facade_bbox) < 4:
        return True
    fx1, fy1, fx2, fy2 = facade_bbox
    for opening in openings:
        x1, y1, x2, y2 = opening["bbox"]
        if x1 < fx1 - 0.02 or y1 < fy1 - 0.02 or x2 > fx2 + 0.02 or y2 > fy2 + 0.02:
            return False
    return True


def _openings_fit_wall_mm(ir: dict[str, Any]) -> bool:
    metric = ir.get("metric") or {}
    wall_length = float(metric.get("facade_width_mm", 0.0) or 0.0)
    wall_height = float(metric.get("facade_height_mm", 0.0) or 0.0)
    if wall_length <= 0 or wall_height <= 0:
        return False
    for opening in ir.get("openings", []):
        geometry = opening.get("geometry") or {}
        offset = float(geometry.get("offset", -1))
        width = float(geometry.get("width", 0))
        sill = float(geometry.get("sill_height", -1))
        height = float(geometry.get("height", 0))
        if offset < 0 or width <= 0 or height <= 0:
            return False
        if offset + width > wall_length + 1.0:
            return False
        if sill + height > wall_height + 1.0:
            return False
    return True


def infer_sketchup_checks(prediction: dict[str, Any]) -> dict[str, bool]:
    openings = prediction.get("openings") or []
    topology = prediction.get("topology") or {}
    scale_hint = prediction.get("pipeline", {}).get("scale_hint")
    ir = prediction_to_ir(prediction)

    has_openings = len(openings) > 0
    has_scale = bool(scale_hint and scale_hint.get("wall_length_mm") and scale_hint.get("wall_height_mm"))
    has_storey = bool(topology.get("storey_count"))
    assigned_storeys = all(opening.get("storey") is not None for opening in openings if opening.get("type") == "window")

    overlaps = False
    for index, opening_a in enumerate(openings):
        for opening_b in openings[index + 1 :]:
            if _opening_overlap(opening_a, opening_b):
                overlaps = True
                break
        if overlaps:
            break

    wall_length = float(scale_hint.get("wall_length_mm", 0)) if scale_hint else 0.0
    wall_height = float(scale_hint.get("wall_height_mm", 0)) if scale_hint else 0.0
    sane_wall = 4000.0 <= wall_length <= 30000.0 and 2400.0 <= wall_height <= 6000.0

    pattern_groups = topology.get("pattern_groups") or []
    component_reuse = any(group.get("members") for group in pattern_groups)

    return {
        "generate_stable": bool(ir and has_openings and has_scale and has_storey and _openings_fit_wall_mm(ir)),
        "editable": bool(ir),
        "openings_are_holes": _openings_within_facade(openings, topology.get("facade_bbox")),
        "no_overlapping_openings": has_openings and not overlaps,
        "correct_storey_assignment": has_openings and assigned_storeys,
        "sane_wall_dimensions": has_scale and sane_wall,
        "component_reuse": component_reuse,
    }


def attach_sketchup_checks(prediction: dict[str, Any]) -> dict[str, bool]:
    checks = infer_sketchup_checks(prediction)
    prediction["sketchup"] = checks
    return checks
