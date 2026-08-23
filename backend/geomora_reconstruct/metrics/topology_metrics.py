from __future__ import annotations

from typing import Any

from .common import accuracy_from_error, relative_error, rounded
from .matching import match_openings_by_iou


def _assignment_accuracy(
    truth_openings: list[dict[str, Any]],
    predicted_openings: list[dict[str, Any]],
    field: str,
    *,
    iou_threshold: float = 0.5,
) -> float | None:
    pairs = match_openings_by_iou(truth_openings, predicted_openings, iou_threshold=iou_threshold)
    comparable = [(truth, prediction) for truth, prediction in pairs if truth.get(field) is not None]
    if not comparable:
        return None
    correct = sum(truth[field] == prediction.get(field) for truth, prediction in comparable)
    return correct / len(comparable)


def evaluate_topology(truth: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any] | None:
    gt = truth.get("topology")
    pred = prediction.get("topology")
    if gt is None or pred is None:
        return None

    storey_error = (
        relative_error(float(pred.get("storey_count", 0)), float(gt["storey_count"]))
        if "storey_count" in gt
        else None
    )
    bay_error = (
        relative_error(float(pred.get("bay_count", 0)), float(gt["bay_count"]))
        if "bay_count" in gt
        else None
    )
    gt_openings = truth.get("openings", [])
    pred_openings = prediction.get("openings", [])
    ground_doors = [item for item in gt_openings if item.get("type") == "door"]
    door_ground = None
    if ground_doors:
        door_pairs = match_openings_by_iou(ground_doors, pred_openings)
        if door_pairs:
            door_ground = sum(prediction.get("storey") == 1 for _, prediction in door_pairs) / len(door_pairs)

    return {
        "storey_count_error": rounded(storey_error),
        "storey_accuracy": rounded(accuracy_from_error(storey_error)),
        "bay_count_error": rounded(bay_error),
        "bay_accuracy": rounded(accuracy_from_error(bay_error)),
        "window_to_storey_assignment_accuracy": rounded(
            _assignment_accuracy(
                [item for item in gt_openings if item.get("type") == "window"],
                pred_openings,
                "storey",
            )
        ),
        "window_to_bay_assignment_accuracy": rounded(
            _assignment_accuracy(
                [item for item in gt_openings if item.get("type") == "window"],
                pred_openings,
                "bay",
            )
        ),
        "door_ground_floor_accuracy": rounded(door_ground),
        "matched_openings": len(match_openings_by_iou(gt_openings, pred_openings)),
    }
