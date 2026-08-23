"""Convert relative-depth transitions into auditable architectural evidence."""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .models import Observation, ObservationGraph, ObservationKind, ObservationSource

NEURAL_OR_GEOMETRIC_METHODS = {
    "depth_anything_v2_small_v1", "depth_anything_v2_small_q4_v1",
    "marigold_v1_1_v1", "midas_v21_v1", "colmap_dense_v1",
}


def depth_discontinuity_observations(
    depth_map: np.ndarray, *, photo_id: str, method: str,
    facade_bbox: list[float] | None = None, max_observations: int = 8,
) -> ObservationGraph:
    if depth_map.ndim != 2 or depth_map.size == 0:
        raise ValueError("Depth map must be a non-empty 2D array")
    height, width = depth_map.shape
    bbox = facade_bbox or [0.0, 0.0, 1.0, 1.0]
    x1 = max(0, min(width - 1, round(float(bbox[0]) * width)))
    y1 = max(0, min(height - 1, round(float(bbox[1]) * height)))
    x2 = max(x1 + 1, min(width, round(float(bbox[2]) * width)))
    y2 = max(y1 + 1, min(height, round(float(bbox[3]) * height)))
    crop = np.nan_to_num(depth_map[y1:y2, x1:x2].astype(np.float32), nan=0.0)
    if crop.shape[0] < 12 or crop.shape[1] < 12:
        return ObservationGraph(photo_id=photo_id, image_width=width, image_height=height,
                                debug={"adapter": "depth_discontinuity_v0.1", "candidate_count": 0, "depth_method": method})

    profile = np.median(crop, axis=1).reshape(-1, 1)
    smooth = cv2.GaussianBlur(profile, (1, 5), sigmaX=0, sigmaY=max(1.0, crop.shape[0] / 180.0)).reshape(-1)
    gradient = np.abs(np.gradient(smooth))
    median = float(np.median(gradient))
    mad = float(np.median(np.abs(gradient - median)))
    threshold = max(0.012, median + 4.0 * max(mad, 1e-4))
    reliable_depth = method in NEURAL_OR_GEOMETRIC_METHODS

    peaks: list[int] = []
    minimum_separation = max(5, round(crop.shape[0] * 0.04))
    for index in np.argsort(gradient)[::-1]:
        index = int(index)
        if gradient[index] < threshold or index < 3 or index >= len(gradient) - 3:
            break
        if all(abs(index - existing) >= minimum_separation for existing in peaks):
            peaks.append(index)
        if len(peaks) >= max_observations:
            break

    observations = []
    for sequence, index in enumerate(sorted(peaks), start=1):
        local_gradient = np.abs(crop[min(index + 1, crop.shape[0] - 1)] - crop[max(index - 1, 0)])
        support = float(np.mean(local_gradient >= max(threshold, 0.02)))
        strength = min(1.0, float(gradient[index]) / max(threshold * 2.5, 1e-6))
        confidence = min(0.95, 0.35 + 0.35 * support + 0.25 * strength)
        role = "depth_discontinuity" if reliable_depth and support >= 0.45 else "depth_edge_proxy"
        semantic_confidence = confidence if role == "depth_discontinuity" else confidence * 0.55
        uncertainties = [] if role == "depth_discontinuity" else ["non_metric_depth_proxy_not_a_storey_boundary"]
        observations.append(Observation(
            id=f"depth_jump_{sequence:03d}", kind=ObservationKind.DEPTH_DISCONTINUITY,
            geometry={"y": round((y1 + index) / height, 5), "x_range": [round(x1 / width, 5), round(x2 / width, 5)],
                      "jump_strength": round(float(gradient[index]), 5), "horizontal_support": round(support, 4)},
            semantic_candidates={role: round(semantic_confidence, 4)}, confidence=confidence,
            sources=[ObservationSource("relative_depth", confidence, {"method": method, "threshold": round(threshold, 6)})],
            uncertainties=uncertainties,
        ))
    return ObservationGraph(
        photo_id=photo_id, image_width=width, image_height=height, observations=observations,
        debug={"adapter": "depth_discontinuity_v0.1", "depth_method": method,
               "metric_depth_evidence": reliable_depth, "candidate_count": len(observations),
               "threshold": round(threshold, 6)},
    )


def depth_observations_to_storey_cues(observations: list[Observation]) -> list[dict[str, Any]]:
    cues = []
    for observation in observations:
        if observation.kind != ObservationKind.DEPTH_DISCONTINUITY:
            continue
        role = max(observation.semantic_candidates, key=observation.semantic_candidates.get, default="depth_edge_proxy")
        cues.append({"id": observation.id, "type": "depth", "role": role,
                     "y": observation.geometry.get("y"), "confidence": observation.confidence,
                     "source": "relative_depth"})
    return cues
