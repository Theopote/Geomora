from __future__ import annotations

from .models import DetectedElement


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


def suppress_overlaps(
    elements: list[DetectedElement],
    iou_threshold: float = 0.4,
) -> list[DetectedElement]:
    ordered = sorted(elements, key=lambda item: item.confidence, reverse=True)
    kept: list[DetectedElement] = []

    for candidate in ordered:
        if any(iou(candidate.bbox_norm, existing.bbox_norm) > iou_threshold for existing in kept):
            continue
        kept.append(candidate)

    return sorted(kept, key=lambda item: item.bbox_norm[0])


def dedupe_doors(elements: list[DetectedElement]) -> list[DetectedElement]:
    doors = [element for element in elements if element.type == "door"]
    windows = [element for element in elements if element.type == "window"]

    if len(doors) > 1:
        best_door = max(doors, key=lambda item: item.confidence)
        merged = windows + [best_door]
    else:
        merged = windows + doors

    return sorted(merged, key=lambda item: (0 if item.type == "door" else 1, item.bbox_norm[0]))
