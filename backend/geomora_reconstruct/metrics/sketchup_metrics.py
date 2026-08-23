from __future__ import annotations

from typing import Any


CHECKS = ("generate_stable", "editable", "openings_are_holes", "no_overlapping_openings", "correct_storey_assignment", "sane_wall_dimensions", "component_reuse")


def evaluate_sketchup(prediction: dict[str, Any]) -> dict[str, Any] | None:
    data = prediction.get("sketchup")
    if data is None:
        return None
    available = {key: bool(data[key]) for key in CHECKS if key in data}
    if not available:
        return None
    return {**available, "pass_rate": round(sum(available.values()) / len(available), 4)}

