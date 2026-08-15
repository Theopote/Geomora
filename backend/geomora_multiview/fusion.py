from __future__ import annotations

import cv2
import numpy as np

from geomora_detect.models import DetectedElement

from .depth import opening_depth_score


def iou(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def transform_bbox_norm(
    bbox_norm: list[float],
    homography: np.ndarray,
    src_width: int,
    src_height: int,
    dst_width: int,
    dst_height: int,
) -> list[float]:
    x1, y1, x2, y2 = bbox_norm
    corners = np.array(
        [
            [x1 * src_width, y1 * src_height],
            [x2 * src_width, y1 * src_height],
            [x2 * src_width, y2 * src_height],
            [x1 * src_width, y2 * src_height],
        ],
        dtype=np.float32,
    ).reshape(1, 4, 2)

    transformed = cv2.perspectiveTransform(corners, homography)[0]
    xs = transformed[:, 0] / dst_width
    ys = transformed[:, 1] / dst_height

    return [
        float(np.clip(xs.min(), 0.0, 1.0)),
        float(np.clip(ys.min(), 0.0, 1.0)),
        float(np.clip(xs.max(), 0.0, 1.0)),
        float(np.clip(ys.max(), 0.0, 1.0)),
    ]


def transform_element(
    element: DetectedElement,
    homography: np.ndarray,
    src_width: int,
    src_height: int,
    dst_width: int,
    dst_height: int,
) -> DetectedElement:
    bbox = transform_bbox_norm(element.bbox_norm, homography, src_width, src_height, dst_width, dst_height)
    return DetectedElement(
        type=element.type,
        bbox_norm=bbox,
        confidence=element.confidence,
    )


def fuse_elements(
    elements: list[DetectedElement],
    depth_map: np.ndarray,
    image_width: int,
    image_height: int,
    iou_threshold: float = 0.35,
) -> list[DetectedElement]:
    scored: list[tuple[DetectedElement, float, str]] = []
    for element in elements:
        depth_score = opening_depth_score(depth_map, element.bbox_norm)
        combined = (0.75 * element.confidence) + (0.25 * depth_score)
        scored.append((element, combined, "primary"))

    scored.sort(key=lambda item: item[1], reverse=True)
    kept: list[DetectedElement] = []
    kept_scores: list[float] = []

    for candidate, combined_score, _source in scored:
        if any(iou(candidate.bbox_norm, existing.bbox_norm) > iou_threshold for existing in kept):
            continue
        kept.append(
            DetectedElement(
                type=candidate.type,
                bbox_norm=candidate.bbox_norm,
                confidence=round(combined_score, 4),
            )
        )
        kept_scores.append(combined_score)

    doors = [element for element in kept if element.type == "door"]
    windows = [element for element in kept if element.type == "window"]
    if len(doors) > 1:
        best_door = max(doors, key=lambda item: item.confidence)
        kept = windows + [best_door]
    else:
        kept = windows + doors

    return sorted(kept, key=lambda item: (0 if item.type == "door" else 1, item.bbox_norm[0]))
