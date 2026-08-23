"""Metric anchor validation and conversion to reconstruction metric truth."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


SURVEYED_STATUS = "surveyed"
PENDING_STATUS = "pending_survey"


def anchor_axis(anchor: dict[str, Any]) -> str:
    explicit = anchor.get("axis")
    if explicit in ("horizontal", "vertical"):
        return explicit
    anchor_id = str(anchor.get("id", ""))
    if "height" in anchor_id:
        return "vertical"
    if "width" in anchor_id:
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
    if anchor_has_distance(anchor) and float(anchor["distance_mm"]) <= 0:
        errors.append(f"{anchor.get('id')}: distance_mm must be positive")
    start = anchor.get("start") or []
    end = anchor.get("end") or []
    if len(start) != 2 or len(end) != 2:
        errors.append(f"{anchor.get('id')}: start/end must be [x, y]")
    return errors


def derive_metric_from_anchors(
    anchors: list[dict[str, Any]],
    *,
    topology: dict[str, Any] | None = None,
) -> dict[str, float] | None:
    metric: dict[str, float] = {}
    for anchor in anchors:
        if not anchor_has_distance(anchor):
            continue
        distance = float(anchor["distance_mm"])
        axis = anchor_axis(anchor)
        if axis == "horizontal":
            metric["facade_width_mm"] = distance
        else:
            metric["facade_height_mm"] = distance

    topology = topology or {}
    storey_count = int(topology.get("storey_count") or 0)
    if metric.get("facade_height_mm") and storey_count > 0:
        metric["storey_height_mm"] = metric["facade_height_mm"] / storey_count

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

    metric = derive_metric_from_anchors(anchors, topology=payload.get("topology"))
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
                "type": update.get("type", "user_distance"),
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
                "distance_mm": width,
                "notes": row.get("notes"),
            }
        )
    if height not in (None, ""):
        updates.append(
            {
                "photo_id": photo_id,
                "anchor_id": "anchor_facade_height",
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
