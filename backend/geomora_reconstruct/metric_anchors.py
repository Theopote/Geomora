"""Metric anchor validation and conversion to reconstruction metric truth."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


SURVEYED_STATUS = "surveyed"
PENDING_STATUS = "pending_survey"
DIRECT_TYPES = {"facade_width", "facade_height"}
SCALE_TYPES = {"segment_distance", "opening_width", "opening_height", "storey_height", "bay_pitch"}
SUPPORTED_TYPES = DIRECT_TYPES | SCALE_TYPES | {"user_distance"}


def _facade_bbox(value: list[float] | None) -> list[float]:
    if isinstance(value, list) and len(value) == 4:
        box = [float(item) for item in value]
        if box[2] > box[0] and box[3] > box[1]:
            return box
    return [0.0, 0.0, 1.0, 1.0]


def anchor_axis(anchor: dict[str, Any]) -> str:
    explicit = anchor.get("axis")
    if explicit in ("horizontal", "vertical"):
        return explicit
    property_name = str(anchor.get("property") or "").lower()
    anchor_type = str(anchor.get("type") or "").lower()
    if property_name in {"height", "storey_height"} or anchor_type in {"facade_height", "opening_height", "storey_height"}:
        return "vertical"
    if property_name in {"width", "bay_pitch"} or anchor_type in {"facade_width", "opening_width", "bay_pitch"}:
        return "horizontal"
    start = anchor.get("start") or [0.0, 0.0]
    end = anchor.get("end") or [0.0, 0.0]
    dx = abs(float(end[0]) - float(start[0]))
    dy = abs(float(end[1]) - float(start[1]))
    return "horizontal" if dx >= dy else "vertical"


def anchor_has_distance(anchor: dict[str, Any]) -> bool:
    distance = anchor.get("distance_mm")
    return distance not in (None, "") and float(distance) > 0


def validate_anchor(anchor: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not anchor.get("id"):
        errors.append("anchor missing id")
    anchor_type = str(anchor.get("type") or "")
    if anchor_type not in SUPPORTED_TYPES:
        errors.append(f"{anchor.get('id')}: unsupported anchor type {anchor_type or '<missing>'}")
    if anchor_type == "segment_distance" and anchor.get("property") not in {"width", "height", "storey_height", "bay_pitch"}:
        errors.append(f"{anchor.get('id')}: segment_distance requires an explicit property")
    raw_distance = anchor.get("distance_mm")
    if raw_distance not in (None, ""):
        try:
            if float(raw_distance) <= 0:
                errors.append(f"{anchor.get('id')}: distance_mm must be positive")
        except (TypeError, ValueError):
            errors.append(f"{anchor.get('id')}: distance_mm must be numeric")
    start = anchor.get("start") or []
    end = anchor.get("end") or []
    if len(start) != 2 or len(end) != 2:
        errors.append(f"{anchor.get('id')}: start/end must be [x, y]")
    elif anchor_type in SCALE_TYPES:
        axis = anchor_axis(anchor)
        span = abs(float(end[0]) - float(start[0])) if axis == "horizontal" else abs(float(end[1]) - float(start[1]))
        if span <= 1e-6:
            errors.append(f"{anchor.get('id')}: anchor span along {axis} axis must be positive")
    return errors


def derive_metric_from_anchors(
    anchors: list[dict[str, Any]],
    *,
    topology: dict[str, Any] | None = None,
    facade_bbox: list[float] | None = None,
) -> dict[str, float] | None:
    box = _facade_bbox(facade_bbox)
    facade_width_norm, facade_height_norm = box[2] - box[0], box[3] - box[1]
    observations: dict[str, list[tuple[float, float]]] = {}

    def observe(field: str, value: float, anchor: dict[str, Any]) -> None:
        priority = str(anchor.get("priority") or "surveyed").lower()
        weight = {"hard": 10.0, "surveyed": 3.0, "soft": 1.0}.get(priority, 3.0)
        observations.setdefault(field, []).append((value, weight))

    for anchor in anchors:
        if not anchor_has_distance(anchor):
            continue
        distance = float(anchor["distance_mm"])
        anchor_type = str(anchor.get("type") or "user_distance")
        axis = anchor_axis(anchor)
        if anchor_type in {"facade_width", "facade_height", "user_distance"}:
            field = "facade_width_mm" if axis == "horizontal" else "facade_height_mm"
            observe(field, distance, anchor)
            continue
        start, end = anchor.get("start") or [], anchor.get("end") or []
        if len(start) != 2 or len(end) != 2:
            continue
        span = abs(float(end[0]) - float(start[0])) if axis == "horizontal" else abs(float(end[1]) - float(start[1]))
        if span <= 1e-6:
            continue
        scale = distance / span
        if axis == "horizontal":
            observe("facade_width_mm", scale * facade_width_norm, anchor)
        else:
            observe("facade_height_mm", scale * facade_height_norm, anchor)
        if anchor_type == "storey_height" or anchor.get("property") == "storey_height":
            observe("storey_height_mm", distance, anchor)

    metric = {
        field: round(sum(value * weight for value, weight in values) / sum(weight for _, weight in values), 1)
        for field, values in observations.items()
    }

    topology = topology or {}
    storey_count = int(topology.get("storey_count") or 0)
    if metric.get("facade_height_mm") and storey_count > 0:
        metric.setdefault("storey_height_mm", round(metric["facade_height_mm"] / storey_count, 1))

    return metric or None


def apply_metric_anchors_to_gt(gt: dict[str, Any]) -> dict[str, Any]:
    payload = dict(gt)
    anchors = payload.get("metric_anchors") or []
    for anchor in anchors:
        if anchor_has_distance(anchor):
            anchor["distance_mm"] = round(float(anchor["distance_mm"]), 1)
            anchor["status"] = SURVEYED_STATUS
            if not anchor.get("surveyed_at"):
                anchor["surveyed_at"] = datetime.now(UTC).isoformat()
        elif anchor.get("status") != SURVEYED_STATUS:
            anchor["status"] = PENDING_STATUS
    payload["metric_anchors"] = anchors

    metric = derive_metric_from_anchors(anchors, topology=payload.get("topology"), facade_bbox=payload.get("facade_bbox"))
    if metric:
        payload["metric"] = metric
    else:
        payload.pop("metric", None)
    return payload


def merge_anchor_updates(
    gt: dict[str, Any],
    updates: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    anchors = [dict(anchor) for anchor in (gt.get("metric_anchors") or [])]
    anchor_by_id = {anchor["id"]: anchor for anchor in anchors if anchor.get("id")}

    for update in updates:
        anchor_id = update.get("anchor_id") or update.get("id")
        if not anchor_id:
            warnings.append("skipped update without anchor_id")
            continue
        anchor = anchor_by_id.get(anchor_id)
        if anchor is None:
            axis = update.get("axis") or anchor_axis({"id": anchor_id})
            if axis == "vertical":
                default_start = [0.05, 0.05]
                default_end = [0.05, 0.95]
            else:
                default_start = [0.05, 0.9]
                default_end = [0.95, 0.9]
            anchor = {
                "id": anchor_id,
                "type": update.get("type", "facade_height" if axis == "vertical" else "facade_width"),
                "target": update.get("target", "facade"),
                "property": update.get("property", "height" if axis == "vertical" else "width"),
                "priority": update.get("priority", "hard"),
                "status": PENDING_STATUS,
                "start": update.get("start", default_start),
                "end": update.get("end", default_end),
                "distance_mm": None,
                "notes": update.get("notes", ""),
            }
            anchors.append(anchor)
            anchor_by_id[anchor_id] = anchor

        if update.get("distance_mm") not in (None, ""):
            distance = float(update["distance_mm"])
            if distance <= 0:
                warnings.append(f"ignored non-positive distance_mm for {anchor_id}")
                continue
            anchor["distance_mm"] = round(distance, 1)
            anchor["status"] = SURVEYED_STATUS
            anchor["surveyed_at"] = update.get("surveyed_at") or datetime.now(UTC).isoformat()
        if update.get("notes"):
            anchor["notes"] = update["notes"]
        if update.get("start"):
            anchor["start"] = [round(float(v), 4) for v in update["start"]]
        if update.get("end"):
            anchor["end"] = [round(float(v), 4) for v in update["end"]]

    merged = dict(gt)
    merged["metric_anchors"] = anchors
    return apply_metric_anchors_to_gt(merged), warnings


def survey_row_to_updates(row: dict[str, Any]) -> list[dict[str, Any]]:
    photo_id = row.get("photo_id")
    if not photo_id:
        return []

    updates: list[dict[str, Any]] = []
    width = row.get("facade_width_mm")
    if width in (None, "") and row.get("distance_mm") not in (None, ""):
        width = row.get("distance_mm")
    height = row.get("facade_height_mm")

    if width not in (None, ""):
        updates.append(
            {
                "photo_id": photo_id,
                "anchor_id": row.get("anchor_id") or "anchor_facade_width",
                "type": "facade_width",
                "target": "facade",
                "property": "width",
                "priority": "hard",
                "distance_mm": width,
                "notes": row.get("notes"),
            }
        )
    if height not in (None, ""):
        updates.append(
            {
                "photo_id": photo_id,
                "anchor_id": "anchor_facade_height",
                "type": "facade_height",
                "target": "facade",
                "property": "height",
                "priority": "hard",
                "distance_mm": height,
                "axis": "vertical",
                "start": row.get("height_start", [0.05, 0.05]),
                "end": row.get("height_end", [0.05, 0.95]),
                "notes": row.get("height_notes") or row.get("notes") or "Surveyed facade height",
            }
        )
    return updates


def anchor_status_report(gt: dict[str, Any]) -> dict[str, Any]:
    anchors = gt.get("metric_anchors") or []
    surveyed = [anchor for anchor in anchors if anchor_has_distance(anchor)]
    pending = [anchor for anchor in anchors if not anchor_has_distance(anchor)]
    return {
        "photo_id": gt.get("photo_id"),
        "anchor_count": len(anchors),
        "surveyed_count": len(surveyed),
        "pending_count": len(pending),
        "has_metric": bool(gt.get("metric")),
        "pending_ids": [anchor.get("id") for anchor in pending],
    }
