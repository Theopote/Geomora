from __future__ import annotations

from typing import Any

from geomora_detect.acceptance_metrics import bbox_iou


def match_openings_by_iou(
    truth_openings: list[dict[str, Any]],
    predicted_openings: list[dict[str, Any]],
    *,
    iou_threshold: float = 0.5,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    used_predictions: set[int] = set()

    for truth in truth_openings:
        best_index = None
        best_iou = 0.0
        for index, prediction in enumerate(predicted_openings):
            if index in used_predictions:
                continue
            if truth.get("type") != prediction.get("type"):
                continue
            iou = bbox_iou(truth["bbox"], prediction["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_index = index
        if best_index is not None and best_iou >= iou_threshold:
            pairs.append((truth, predicted_openings[best_index]))
            used_predictions.add(best_index)
    return pairs
