"""Conservative horizontal-structure observations for storey hypotheses."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import math
from collections import Counter

import cv2

from geomora_detect.image_io import imread_bgr

from .models import Observation, ObservationGraph, ObservationKind, ObservationSource


def _pixel_facade(bbox: list[float] | None, width: int, height: int) -> tuple[int, int, int, int]:
    if not bbox or len(bbox) < 4:
        return 0, 0, width, height
    x1, y1, x2, y2 = bbox
    return (
        max(0, min(width - 1, round(float(x1) * width))),
        max(0, min(height - 1, round(float(y1) * height))),
        max(1, min(width, round(float(x2) * width))),
        max(1, min(height, round(float(y2) * height))),
    )


def detect_horizontal_structure_observations(
    image_path: str | Path,
    *,
    photo_id: str,
    facade_bbox: list[float] | None = None,
    max_observations: int = 16,
) -> ObservationGraph:
    """Detect long horizontal segments, retaining them as non-semantic evidence.

    The adapter deliberately labels lines as ``horizontal_structure`` rather
    than floor slabs. Architectural semantics must come from another detector,
    depth evidence, VLM evidence, or review.
    """
    image = imread_bgr(image_path)
    height, width = image.shape[:2]
    fx1, fy1, fx2, fy2 = _pixel_facade(facade_bbox, width, height)
    crop = image[fy1:fy2, fx1:fx2]
    crop_height, crop_width = crop.shape[:2]
    if crop_width < 20 or crop_height < 20:
        return ObservationGraph(photo_id=photo_id, image_width=width, image_height=height,
                                debug={"adapter": "horizontal_structure_v0.1", "candidate_count": 0})

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 45, 135)
    lines = cv2.HoughLinesP(
        edges, 1, math.pi / 180,
        threshold=max(30, crop_width // 12),
        minLineLength=max(24, round(crop_width * 0.28)),
        maxLineGap=max(8, round(crop_width * 0.035)),
    )

    candidates: list[dict[str, float]] = []
    for raw in lines if lines is not None else []:
        values = raw.reshape(-1)
        if len(values) < 4:
            continue
        x1, y1, x2, y2 = (int(value) for value in values[:4])
        length = max(abs(x2 - x1), 1)
        slope = abs(y2 - y1) / length
        if slope > 0.035:
            continue
        coverage = min(1.0, length / crop_width)
        confidence = min(0.92, 0.35 + 0.65 * coverage) * (1.0 - slope)
        candidates.append({
            "x1": (fx1 + min(x1, x2)) / width,
            "x2": (fx1 + max(x1, x2)) / width,
            "y": (fy1 + (y1 + y2) / 2.0) / height,
            "confidence": confidence,
        })

    # Hough commonly returns both edges of one thick feature. Cluster them into
    # a single observation, keeping their union and strongest confidence.
    clusters: list[list[dict[str, float]]] = []
    for item in sorted(candidates, key=lambda value: value["y"]):
        if not clusters or abs(item["y"] - sum(v["y"] for v in clusters[-1]) / len(clusters[-1])) > 0.012:
            clusters.append([item])
        else:
            clusters[-1].append(item)

    observations: list[Observation] = []
    ranked = sorted(clusters, key=lambda group: max(item["confidence"] for item in group), reverse=True)
    for index, group in enumerate(ranked[:max_observations], start=1):
        weights = [max(item["confidence"], 0.01) for item in group]
        y = sum(item["y"] * weight for item, weight in zip(group, weights)) / sum(weights)
        confidence = max(item["confidence"] for item in group)
        observations.append(Observation(
            id=f"horizontal_{index:03d}",
            kind=ObservationKind.HORIZONTAL_LINE,
            geometry={"y": round(y, 5), "x_range": [round(min(i["x1"] for i in group), 5), round(max(i["x2"] for i in group), 5)]},
            semantic_candidates={"horizontal_structure": round(confidence, 4)},
            confidence=confidence,
            sources=[ObservationSource("classical_line_detector", confidence, {"algorithm": "canny_hough_v0.1", "segment_count": len(group)})],
            uncertainties=["architectural_role_unclassified"],
        ))
    observations.sort(key=lambda item: float(item.geometry["y"]))
    return ObservationGraph(
        photo_id=photo_id, image_width=width, image_height=height, observations=observations,
        debug={"adapter": "horizontal_structure_v0.1", "raw_segment_count": len(candidates),
               "candidate_count": len(observations), "facade_bbox": facade_bbox},
    )


def horizontal_observations_to_storey_cues(observations: list[Observation]) -> list[dict[str, Any]]:
    cues = []
    for observation in observations:
        if observation.kind != ObservationKind.HORIZONTAL_LINE or "y" not in observation.geometry:
            continue
        role = max(observation.semantic_candidates, key=observation.semantic_candidates.get, default="horizontal_structure")
        cues.append({"id": observation.id, "type": "horizontal_line", "role": role,
                     "y": observation.geometry["y"], "confidence": observation.confidence,
                     "source": observation.sources[0].type if observation.sources else "observation_layer"})
    return cues


def classify_horizontal_structure_roles(
    observations: list[Observation],
    *,
    openings: list[dict[str, Any]],
    facade_bbox: list[float] | None = None,
) -> dict[str, int]:
    """Attach conservative architectural roles using opening-layout context.

    This classifier only emits ``floor_slab`` when a long line lies in the
    clear gap between two window rows. It therefore cannot turn a lone cornice
    or window lintel into a new storey boundary.
    """
    windows = [item for item in openings if item.get("type") == "window" and len(item.get("bbox", [])) >= 4]
    facade = facade_bbox or [0.0, 0.0, 1.0, 1.0]
    facade_width = max(float(facade[2]) - float(facade[0]), 1e-6)

    rows: list[list[dict[str, Any]]] = []
    for window in sorted(windows, key=lambda item: (item["bbox"][1] + item["bbox"][3]) / 2.0):
        center = (window["bbox"][1] + window["bbox"][3]) / 2.0
        if not rows:
            rows.append([window])
            continue
        previous_center = sum((item["bbox"][1] + item["bbox"][3]) / 2.0 for item in rows[-1]) / len(rows[-1])
        if abs(center - previous_center) <= 0.08:
            rows[-1].append(window)
        else:
            rows.append([window])
    stable_rows = [row for row in rows if len(row) >= 2]

    role_counts: Counter[str] = Counter()
    for observation in observations:
        if observation.kind != ObservationKind.HORIZONTAL_LINE:
            continue
        y = float(observation.geometry.get("y", -1.0))
        x_range = observation.geometry.get("x_range") or [0.0, 0.0]
        coverage = max(0.0, float(x_range[1]) - float(x_range[0])) / facade_width
        role = "horizontal_structure"
        semantic_confidence = observation.confidence * 0.55

        # A slab candidate needs two independently stable opening rows and a
        # line in their empty inter-storey zone, not merely near an opening edge.
        for upper, lower in zip(stable_rows[:-1], stable_rows[1:]):
            upper_bottom = max(float(item["bbox"][3]) for item in upper)
            lower_top = min(float(item["bbox"][1]) for item in lower)
            margin = min(0.025, max(0.008, (lower_top - upper_bottom) * 0.12))
            if coverage >= 0.55 and upper_bottom + margin <= y <= lower_top - margin:
                role = "floor_slab"
                semantic_confidence = min(0.94, observation.confidence * (0.72 + 0.22 * min(coverage, 1.0)))
                break

        if role == "horizontal_structure" and windows:
            top_hits = sum(abs(y - float(item["bbox"][1])) <= 0.015 for item in windows)
            bottom_hits = sum(abs(y - float(item["bbox"][3])) <= 0.015 for item in windows)
            if max(top_hits, bottom_hits) >= 2:
                role = "opening_alignment"
                semantic_confidence = min(0.9, observation.confidence * 0.82)
            else:
                topmost = min(float(item["bbox"][1]) for item in windows)
                if coverage >= 0.65 and float(facade[1]) <= y < topmost - 0.018:
                    role = "cornice"
                    semantic_confidence = min(0.88, observation.confidence * 0.78)

        observation.semantic_candidates = {
            role: round(semantic_confidence, 4),
            "horizontal_structure": round(max(0.05, observation.confidence * 0.35), 4),
        }
        if role != "horizontal_structure":
            observation.uncertainties = [item for item in observation.uncertainties if item != "architectural_role_unclassified"]
            observation.uncertainties.append("architectural_role_inferred_from_opening_context")
        role_counts[role] += 1
    return dict(sorted(role_counts.items()))
