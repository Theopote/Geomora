"""Occlusion-aware hidden-opening hypotheses that never become observed geometry."""
from __future__ import annotations

from statistics import median
from typing import Any

from ..vlm_evidence import OcclusionEvidence


def _center(bbox: list[float]) -> tuple[float, float]:
    return (float(bbox[0] + bbox[2]) / 2.0, float(bbox[1] + bbox[3]) / 2.0)


def _overlap_ratio(first: list[float], second: list[float]) -> float:
    x = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    y = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    area = max((first[2] - first[0]) * (first[3] - first[1]), 1e-9)
    return x * y / area


def _fundamental_pitch(centers: list[float]) -> tuple[float | None, float]:
    gaps = [centers[index + 1] - centers[index] for index in range(len(centers) - 1)]
    if len(gaps) < 2:
        return None, 0.0
    pitch = min(gap for gap in gaps if gap > 1e-4)
    residuals = [abs(gap / pitch - round(gap / pitch)) for gap in gaps]
    consistency = max(0.0, 1.0 - max(residuals) / 0.18)
    return (pitch, consistency) if consistency > 0 else (None, 0.0)


def infer_hidden_opening_hypotheses(
    openings: list[dict[str, Any]],
    occlusions: list[OcclusionEvidence],
) -> list[dict[str, Any]]:
    by_storey: dict[int, list[dict[str, Any]]] = {}
    for opening in openings:
        if opening.get("type") == "window" and opening.get("storey") is not None:
            by_storey.setdefault(int(opening["storey"]), []).append(opening)

    hypotheses = []
    for occlusion_index, occlusion in enumerate(occlusions, start=1):
        if not occlusion.likely_hidden_opening or occlusion.confidence < 0.5:
            continue
        for storey, row in by_storey.items():
            if len(row) < 3:
                continue
            row = sorted(row, key=lambda item: _center(item["bbox"])[0])
            centers = [_center(item["bbox"])[0] for item in row]
            pitch, consistency = _fundamental_pitch(centers)
            if pitch is None or consistency < 0.55:
                continue
            widths = [item["bbox"][2] - item["bbox"][0] for item in row]
            heights = [item["bbox"][3] - item["bbox"][1] for item in row]
            center_y = median(_center(item["bbox"])[1] for item in row)
            width, height = median(widths), median(heights)
            start = min(centers)
            end = max(centers)
            steps = round((end - start) / pitch)
            predicted = [start + step * pitch for step in range(steps + 1)]
            # One-step extrapolation is allowed only when the occlusion itself
            # covers it; this avoids inventing an unlimited facade grid.
            predicted.extend([start - pitch, end + pitch])
            for center_x in predicted:
                if any(abs(center_x - observed) <= pitch * 0.28 for observed in centers):
                    continue
                bbox = [center_x - width / 2, center_y - height / 2, center_x + width / 2, center_y + height / 2]
                overlap = _overlap_ratio(bbox, occlusion.region)
                if overlap < 0.35:
                    continue
                confidence = min(0.78, occlusion.confidence * consistency * 0.78)
                hypotheses.append({
                    "id": f"hidden_s{storey}_{len(hypotheses) + 1:03d}", "type": "window",
                    "bbox": [round(value, 4) for value in bbox], "storey": storey,
                    "status": "hidden_hypothesis", "confidence": round(confidence, 4),
                    "evidence": {"occlusion_id": f"vlm_occlusion_{occlusion_index:03d}",
                                 "reason": occlusion.reason, "pattern_pitch": round(pitch, 4),
                                 "pattern_members": [item.get("id") for item in row if item.get("id")],
                                 "occlusion_overlap": round(overlap, 4)},
                    "requires_confirmation": True,
                })
    # Multiple rows or extrapolations can converge on one location.
    unique = []
    for item in sorted(hypotheses, key=lambda value: (-value["confidence"], value["id"])):
        cx, cy = _center(item["bbox"])
        if any(abs(cx - _center(existing["bbox"])[0]) < 0.02 and abs(cy - _center(existing["bbox"])[1]) < 0.02 for existing in unique):
            continue
        unique.append(item)
    return unique
