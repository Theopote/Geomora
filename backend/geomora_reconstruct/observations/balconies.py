"""Cross-modal balcony slab hypotheses."""
from __future__ import annotations

from typing import Any

from .models import Observation, ObservationKind, ObservationSource


def _range_overlap(first: list[float], second: list[float]) -> float:
    return max(0.0, min(float(first[1]), float(second[1])) - max(float(first[0]), float(second[0])))


def infer_balcony_slab_observations(
    horizontal_lines: list[Observation],
    depth_jumps: list[Observation],
    *,
    openings: list[dict[str, Any]],
    facade_bbox: list[float] | None = None,
) -> list[Observation]:
    """Require line + reliable depth jump + supported openings above it."""
    facade = facade_bbox or [0.0, 0.0, 1.0, 1.0]
    facade_width = max(float(facade[2]) - float(facade[0]), 1e-6)
    windows = [item for item in openings if item.get("type") == "window" and len(item.get("bbox", [])) >= 4]
    reliable_jumps = [
        item for item in depth_jumps
        if item.kind == ObservationKind.DEPTH_DISCONTINUITY
        and "depth_discontinuity" in item.semantic_candidates
    ]
    candidates: list[Observation] = []
    used_pairs: set[tuple[str, str]] = set()
    for line in horizontal_lines:
        if line.kind != ObservationKind.HORIZONTAL_LINE:
            continue
        line_role = max(line.semantic_candidates, key=line.semantic_candidates.get, default="horizontal_structure")
        if line_role in {"floor_slab", "cornice"}:
            continue
        line_y = float(line.geometry.get("y", -1.0))
        line_range = line.geometry.get("x_range") or [0.0, 0.0]
        coverage = (float(line_range[1]) - float(line_range[0])) / facade_width
        if coverage < 0.25 or coverage > 0.82:
            continue
        supported_windows = []
        for window in windows:
            bbox = window["bbox"]
            vertical_gap = line_y - float(bbox[3])
            overlap = _range_overlap(line_range, [bbox[0], bbox[2]])
            if -0.015 <= vertical_gap <= 0.13 and overlap >= 0.3 * (float(bbox[2]) - float(bbox[0])):
                supported_windows.append(window)
        if not supported_windows:
            continue
        for jump in reliable_jumps:
            jump_y = float(jump.geometry.get("y", -1.0))
            if abs(line_y - jump_y) > 0.025:
                continue
            pair = (line.id, jump.id)
            if pair in used_pairs:
                continue
            used_pairs.add(pair)
            confidence = min(0.94, 0.25 + 0.35 * line.confidence + 0.3 * jump.confidence + 0.04 * len(supported_windows))
            candidates.append(Observation(
                id=f"balcony_{len(candidates) + 1:03d}", kind=ObservationKind.BALCONY_CANDIDATE,
                geometry={"y": round((line_y + jump_y) / 2.0, 5), "x_range": list(line_range),
                          "supported_opening_count": len(supported_windows),
                          "supported_opening_ids": [item.get("id") for item in supported_windows if item.get("id")]},
                semantic_candidates={"balcony_slab": round(confidence, 4)}, confidence=confidence,
                sources=[
                    ObservationSource("horizontal_structure", line.confidence, {"observation_id": line.id}),
                    ObservationSource("relative_depth", jump.confidence, {"observation_id": jump.id}),
                ],
                uncertainties=["balcony_role_inferred_from_cross_modal_context"],
            ))
    return candidates


def balcony_observations_to_storey_cues(observations: list[Observation]) -> list[dict[str, Any]]:
    return [
        {"id": item.id, "type": "balcony", "role": "balcony_slab",
         "y": item.geometry["y"], "confidence": item.confidence, "source": "cross_modal_balcony"}
        for item in observations if item.kind == ObservationKind.BALCONY_CANDIDATE
    ]
