from __future__ import annotations

from statistics import median
from typing import Any

from .facade import bbox_center, bbox_size


def cluster_sorted(values: list[tuple[int, float]], tolerance: float) -> dict[int, int]:
    if not values:
        return {}

    ordered = sorted(values, key=lambda item: item[1])
    clusters: list[list[tuple[int, float]]] = [[ordered[0]]]
    for item in ordered[1:]:
        if abs(item[1] - clusters[-1][-1][1]) <= tolerance:
            clusters[-1].append(item)
        else:
            clusters.append([item])

    labels: dict[int, int] = {}
    for cluster_id, cluster in enumerate(clusters, start=1):
        for index, _value in cluster:
            labels[index] = cluster_id
    return labels


def is_plausible_opening(opening: dict[str, Any], *, facade_bbox: list[float] | None = None) -> bool:
    width, height = bbox_size(opening["bbox"])
    if width <= 0.02 or height <= 0.05:
        return False

    area = width * height
    if area > 0.20:
        return False

    x1, y1, x2, y2 = opening["bbox"]
    if facade_bbox and len(facade_bbox) >= 4:
        fx1, fy1, fx2, fy2 = facade_bbox
        overlap_x = max(0.0, min(x2, fx2) - max(x1, fx1))
        overlap_y = max(0.0, min(y2, fy2) - max(y1, fy1))
        overlap_area = overlap_x * overlap_y
        if area > 0 and overlap_area / area < 0.45:
            return False

    opening_type = opening.get("type")
    aspect = width / height if height > 0 else 0.0

    if opening_type == "window":
        if height > 0.40 or width > 0.50:
            return False
        if aspect > 4.5 or aspect < 0.15:
            return False
        if x1 <= 0.005 and width < 0.05:
            return False
        if x2 >= 0.995 and width < 0.05:
            return False
        return True

    if opening_type == "door":
        if height < 0.10 or width > 0.45:
            return False
        if aspect > 1.8:
            return False
        return True

    return area <= 0.12


def partition_openings(
    openings: list[dict[str, Any]],
    *,
    facade_bbox: list[float] | None = None,
) -> tuple[list[tuple[int, dict]], list[tuple[int, dict]]]:
    core: list[tuple[int, dict]] = []
    outliers: list[tuple[int, dict]] = []
    for index, opening in enumerate(openings):
        if is_plausible_opening(opening, facade_bbox=facade_bbox):
            core.append((index, opening))
        else:
            outliers.append((index, opening))
    return core, outliers


def adaptive_storey_tolerance(windows: list[dict]) -> float:
    heights = [bbox_size(window["bbox"])[1] for window in windows if window.get("type") == "window"]
    if not heights:
        return 0.08
    return min(0.10, max(0.05, median(heights) * 0.45))


def adaptive_bay_tolerance(windows: list[dict]) -> float:
    widths = [bbox_size(window["bbox"])[0] for window in windows if window.get("type") == "window"]
    if not widths:
        return 0.10
    return min(0.12, max(0.05, median(widths) * 0.55))
