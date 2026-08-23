from __future__ import annotations

from typing import Any

from .common import mean, relative_error, rounded


FIELDS = ("facade_width_mm", "facade_height_mm", "storey_height_mm", "window_width_mm", "window_height_mm")


def evaluate_scale(truth: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any] | None:
    gt = truth.get("metric")
    pred = prediction.get("metric")
    if gt is None or pred is None:
        return None
    errors = {field: relative_error(float(pred[field]), float(gt[field])) for field in FIELDS if field in gt and field in pred}
    if not errors:
        return None
    result = {f"{field}_error": rounded(value) for field, value in errors.items()}
    result["mean_relative_error"] = rounded(mean(value for value in errors.values() if value is not None))
    return result

