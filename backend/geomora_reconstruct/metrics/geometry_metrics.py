from __future__ import annotations

from typing import Any

from ..geometry_inference import opening_geometry_ratios
from .common import mean, rounded
from .matching import match_openings_by_iou


def evaluate_geometry(
    truth: dict[str, Any],
    prediction: dict[str, Any],
    *,
    iou_threshold: float = 0.5,
) -> dict[str, Any] | None:
    if not all(key in truth and key in prediction for key in ("facade", "openings", "topology")):
        return None

    errors: list[float] = []
    width_errors: list[float] = []
    height_errors: list[float] = []
    sill_errors: list[float] = []
    pairs = match_openings_by_iou(
        truth["openings"],
        prediction["openings"],
        iou_threshold=iou_threshold,
    )

    for expected, actual in pairs:
        expected_ratios = opening_geometry_ratios(expected, truth["facade"], truth["topology"])
        actual_ratios = opening_geometry_ratios(actual, prediction["facade"], prediction["topology"])
        for key in ("width_facade", "height_storey", "sill_storey"):
            delta = abs(actual_ratios[key] - expected_ratios[key])
            errors.append(delta)
        width_errors.append(abs(actual_ratios["width_facade"] - expected_ratios["width_facade"]))
        height_errors.append(abs(actual_ratios["height_storey"] - expected_ratios["height_storey"]))
        sill_errors.append(abs(actual_ratios["sill_storey"] - expected_ratios["sill_storey"]))

    return {
        "normalized_mae": rounded(mean(errors)),
        "width_facade_mae": rounded(mean(width_errors)),
        "height_storey_mae": rounded(mean(height_errors)),
        "sill_storey_mae": rounded(mean(sill_errors)),
        "matched_openings": len(pairs),
        "ground_truth_openings": len(truth["openings"]),
        "iou_threshold": iou_threshold,
    }
