from __future__ import annotations

from typing import Any

from .common import mean, rounded


def _ratios(item: dict[str, Any], facade: dict[str, float], topology: dict[str, Any]) -> dict[str, float]:
    x1, y1, x2, y2 = item["bbox"]
    facade_width = facade.get("width", 1.0)
    facade_height = facade.get("height", 1.0)
    storeys = max(int(topology.get("storey_count", 1)), 1)
    storey_height = facade_height / storeys
    return {
        "width_facade": (x2 - x1) / facade_width,
        "height_storey": (y2 - y1) / storey_height,
        "sill_storey": (facade_height - y2) % storey_height / storey_height,
    }


def evaluate_geometry(truth: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any] | None:
    if not all(key in truth and key in prediction for key in ("facade", "openings", "topology")):
        return None
    predicted_by_id = {item.get("id"): item for item in prediction["openings"]}
    errors: list[float] = []
    matched = 0
    for expected in truth["openings"]:
        actual = predicted_by_id.get(expected.get("id"))
        if actual is None:
            continue
        expected_ratios = _ratios(expected, truth["facade"], truth["topology"])
        actual_ratios = _ratios(actual, prediction["facade"], prediction["topology"])
        errors.extend(abs(actual_ratios[key] - value) for key, value in expected_ratios.items())
        matched += 1
    return {
        "normalized_mae": rounded(mean(errors)),
        "matched_openings": matched,
        "ground_truth_openings": len(truth["openings"]),
    }

