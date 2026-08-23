"""Evidence-backed door/storey hypotheses."""
from __future__ import annotations

from typing import Any

from .facade import bbox_center

LEGACY_DOOR_FLOOR_Y_MIN = 0.72
BOTTOM_GAP_RATIO_MAX = 0.12


def infer_door_storey_hypothesis(
    door: dict[str, Any], *, facade_bbox: list[float], storeys: list,
    facade_bounds_observed: bool,
) -> dict[str, Any]:
    bbox = door["bbox"]
    facade_height = max(float(facade_bbox[3]) - float(facade_bbox[1]), 1e-6)
    bottom_gap_ratio = abs(float(facade_bbox[3]) - float(bbox[3])) / facade_height
    evidence = ["door_detector"]
    confidence = min(0.75, max(0.3, float(door.get("confidence", 0.65)) * 0.72))

    if bottom_gap_ratio <= BOTTOM_GAP_RATIO_MAX:
        evidence.append("near_observed_facade_bottom" if facade_bounds_observed else "near_inferred_facade_bottom")
        candidate_storey = 1
        confidence += 0.18 if facade_bounds_observed else 0.07
    elif storeys:
        center_y = bbox_center(bbox)[1]
        nearest = min(storeys, key=lambda band: abs((band.y_min + band.y_max) / 2.0 - center_y))
        candidate_storey = nearest.id
        evidence.append("nearest_storey_band")
        confidence = min(confidence, float(nearest.confidence) * 0.82)
    else:
        candidate_storey = 1
        evidence.append("fallback_without_storey_geometry")
        confidence = min(confidence, 0.35)

    if float(bbox[3]) >= LEGACY_DOOR_FLOOR_Y_MIN:
        evidence.append("legacy_low_image_position")
        confidence += 0.03

    confidence = max(0.0, min(0.92, confidence))
    return {
        "hypothesis": "ground_floor_door" if candidate_storey == 1 else "door_storey_assignment",
        "candidate_storey": int(candidate_storey),
        "confidence": round(confidence, 4),
        "status": "hypothesized",
        "evidence": evidence,
        "measurements": {"facade_bottom_gap_ratio": round(bottom_gap_ratio, 4)},
        "requires_confirmation": confidence < 0.8,
    }
