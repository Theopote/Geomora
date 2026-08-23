from __future__ import annotations

from typing import Any

from .common import accuracy_from_error, relative_error, rounded


def _assignment_accuracy(truth: list[dict[str, Any]], prediction: list[dict[str, Any]], field: str) -> float | None:
    predicted_by_id = {item.get("id"): item for item in prediction if item.get("id")}
    comparable = [item for item in truth if item.get("id") and item.get(field) is not None]
    if not comparable:
        return None
    correct = sum(
        predicted_by_id.get(item["id"], {}).get(field) == item[field]
        for item in comparable
    )
    return correct / len(comparable)


def evaluate_topology(truth: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any] | None:
    gt = truth.get("topology")
    pred = prediction.get("topology")
    if gt is None or pred is None:
        return None

    storey_error = relative_error(float(pred.get("storey_count", 0)), float(gt["storey_count"])) if "storey_count" in gt else None
    bay_error = relative_error(float(pred.get("bay_count", 0)), float(gt["bay_count"])) if "bay_count" in gt else None
    gt_openings = truth.get("openings", [])
    pred_openings = prediction.get("openings", [])
    ground_doors = [item for item in gt_openings if item.get("type") == "door"]
    door_ground = None
    if ground_doors:
        predicted_by_id = {item.get("id"): item for item in pred_openings}
        door_ground = sum(
            predicted_by_id.get(item.get("id"), {}).get("storey") == 1
            for item in ground_doors
        ) / len(ground_doors)

    return {
        "storey_count_error": rounded(storey_error),
        "storey_accuracy": rounded(accuracy_from_error(storey_error)),
        "bay_count_error": rounded(bay_error),
        "bay_accuracy": rounded(accuracy_from_error(bay_error)),
        "window_to_storey_assignment_accuracy": rounded(_assignment_accuracy(gt_openings, pred_openings, "storey")),
        "window_to_bay_assignment_accuracy": rounded(_assignment_accuracy(gt_openings, pred_openings, "bay")),
        "door_ground_floor_accuracy": rounded(door_ground),
    }

