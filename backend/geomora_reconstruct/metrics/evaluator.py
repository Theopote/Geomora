from __future__ import annotations

from typing import Any

from .detection_metrics import evaluate_detection
from .geometry_metrics import evaluate_geometry
from .rationalization_metrics import evaluate_rationalization
from .scale_metrics import evaluate_scale
from .sketchup_metrics import evaluate_sketchup
from .topology_metrics import evaluate_topology


WEIGHTS = {"detection": 25.0, "topology": 25.0, "geometry": 20.0, "scale": 10.0, "rationalization": 10.0, "sketchup": 10.0}


def _score(groups: dict[str, dict[str, Any] | None]) -> tuple[float | None, float]:
    values: dict[str, float] = {}
    detection = groups["detection"]
    if detection:
        values["detection"] = (detection["window"]["f1"] + detection["door"]["f1"]) / 2
    topology = groups["topology"]
    if topology:
        candidates = [topology[key] for key in ("storey_accuracy", "bay_accuracy", "window_to_storey_assignment_accuracy", "window_to_bay_assignment_accuracy", "door_ground_floor_accuracy") if topology.get(key) is not None]
        if candidates:
            values["topology"] = sum(candidates) / len(candidates)
    geometry = groups["geometry"]
    if geometry and geometry.get("normalized_mae") is not None:
        values["geometry"] = max(0.0, 1.0 - geometry["normalized_mae"])
    scale = groups["scale"]
    if scale:
        values["scale"] = max(0.0, 1.0 - scale["mean_relative_error"])
    rationalization = groups["rationalization"]
    if rationalization:
        values["rationalization"] = max(0.0, min(1.0, rationalization["mean_improvement"]))
    sketchup = groups["sketchup"]
    if sketchup:
        values["sketchup"] = sketchup["pass_rate"]
    evaluated_weight = sum(WEIGHTS[key] for key in values)
    coverage = evaluated_weight / sum(WEIGHTS.values())
    if not values:
        return None, coverage
    score = sum(values[key] * WEIGHTS[key] for key in values) / evaluated_weight * 100
    return round(score, 1), round(coverage, 4)


def evaluate_reconstruction(truth: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
    if truth.get("photo_id") != prediction.get("photo_id"):
        raise ValueError("ground truth and prediction photo_id must match")
    groups = {
        "detection": evaluate_detection(truth, prediction),
        "topology": evaluate_topology(truth, prediction),
        "geometry": evaluate_geometry(truth, prediction),
        "scale": evaluate_scale(truth, prediction),
        "rationalization": evaluate_rationalization(prediction),
        "sketchup": evaluate_sketchup(prediction),
    }
    rqs, coverage = _score(groups)
    return {
        "photo_id": truth["photo_id"],
        **groups,
        "rqs": rqs,
        "coverage": coverage,
        "not_evaluated": [key for key, value in groups.items() if value is None],
    }

