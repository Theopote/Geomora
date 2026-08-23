from __future__ import annotations

from typing import Any

from geomora_detect.acceptance_metrics import match_class_boxes


def evaluate_detection(
    truth: dict[str, Any], prediction: dict[str, Any], *, iou_threshold: float = 0.5
) -> dict[str, Any] | None:
    truth_openings = truth.get("openings")
    predicted_openings = prediction.get("openings")
    if truth_openings is None or predicted_openings is None:
        return None

    result: dict[str, Any] = {"iou_threshold": iou_threshold}
    for kind in ("window", "door"):
        gt = [item["bbox"] for item in truth_openings if item.get("type") == kind]
        pred = [item["bbox"] for item in predicted_openings if item.get("type") == kind]
        result[kind] = match_class_boxes(pred, gt, iou_threshold=iou_threshold).to_dict()
    return result

