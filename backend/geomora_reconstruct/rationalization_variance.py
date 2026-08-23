"""Compute rationalization variance from opening geometry."""
from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


VARIANCE_FIELDS = (
    "width_variance",
    "height_variance",
    "sill_variance",
    "spacing_variance",
    "alignment_deviation",
)


def _opening_rows(openings: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    rows: dict[int, list[dict[str, Any]]] = {}
    for opening in openings:
        if opening.get("type") != "window":
            continue
        storey = int(opening.get("storey") or 1)
        rows.setdefault(storey, []).append(opening)
    return [sorted(row, key=lambda item: item["bbox"][0]) for row in rows.values() if len(row) >= 2]


def _row_metrics(row: list[dict[str, Any]]) -> dict[str, float]:
    widths = [item["bbox"][2] - item["bbox"][0] for item in row]
    heights = [item["bbox"][3] - item["bbox"][1] for item in row]
    sills = [item["bbox"][3] for item in row]
    centers_x = [(item["bbox"][0] + item["bbox"][2]) / 2.0 for item in row]
    spacings = [centers_x[index + 1] - centers_x[index] for index in range(len(centers_x) - 1)]

    def normalized_spread(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        center = mean(values)
        if center <= 0:
            return 0.0
        return pstdev(values) / center

    alignment = normalized_spread(sills)
    if len(centers_x) >= 2:
        alignment = max(alignment, normalized_spread(centers_x))

    return {
        "width_variance": normalized_spread(widths),
        "height_variance": normalized_spread(heights),
        "sill_variance": normalized_spread(sills),
        "spacing_variance": normalized_spread(spacings) if spacings else 0.0,
        "alignment_deviation": alignment,
    }


def compute_rationalization_variance(openings: list[dict[str, Any]]) -> dict[str, float] | None:
    rows = _opening_rows(openings)
    if not rows:
        return None

    aggregates: dict[str, list[float]] = {field: [] for field in VARIANCE_FIELDS}
    for row in rows:
        metrics = _row_metrics(row)
        for field in VARIANCE_FIELDS:
            aggregates[field].append(metrics[field])

    return {field: round(mean(values), 4) for field, values in aggregates.items()}


def equalize_row(openings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = _opening_rows(openings)
    if not rows:
        return openings

    by_id = {item["id"]: dict(item) for item in openings if item.get("id")}
    for row in rows:
        target_width = mean(item["bbox"][2] - item["bbox"][0] for item in row)
        target_height = mean(item["bbox"][3] - item["bbox"][1] for item in row)
        target_sill = mean(item["bbox"][3] for item in row)
        left = min(item["bbox"][0] for item in row)
        right = max(item["bbox"][2] for item in row)
        span = right - left
        gap = (span - target_width * len(row)) / max(len(row) - 1, 1)
        cursor = left
        for item in row:
            opening_id = item["id"]
            if opening_id not in by_id:
                continue
            x1 = cursor
            x2 = x1 + target_width
            y2 = target_sill
            y1 = y2 - target_height
            by_id[opening_id]["bbox"] = [round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)]
            cursor = x2 + gap

    return [by_id.get(item["id"], item) if item.get("id") else item for item in openings]


def attach_rationalization_metrics(prediction: dict[str, Any]) -> dict[str, float] | None:
    openings = prediction.get("openings") or []
    if prediction.get("constraint_solution"):
        observed_openings = []
        for opening in openings:
            item = dict(opening)
            item["bbox"] = list(opening.get("observed_bbox") or opening["bbox"])
            observed_openings.append(item)
        before = compute_rationalization_variance(observed_openings)
        after = compute_rationalization_variance(openings)
        if before is None or after is None:
            return None
        prediction["rationalization_before"] = before
        prediction["rationalization_after"] = after
        return after
    before = compute_rationalization_variance(openings)
    if before is None:
        return None
    after_openings = equalize_row(openings)
    after = compute_rationalization_variance(after_openings)
    if after is None:
        return None
    prediction["rationalization_before"] = before
    prediction["rationalization_after"] = after
    return after
