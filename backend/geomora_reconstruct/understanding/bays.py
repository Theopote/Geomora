from __future__ import annotations

from .facade import bbox_center
from .openings import cluster_sorted
from .result import BayColumn


def infer_bay_columns(
    windows: list[dict],
    *,
    tolerance: float,
) -> tuple[list[BayColumn], dict[int, int]]:
    if not windows:
        return [], {}

    indexed = [(index, bbox_center(window["bbox"])[0]) for index, window in enumerate(windows)]
    raw = cluster_sorted(indexed, tolerance)
    cluster_centers: dict[int, list[float]] = {}
    for index, cluster_id in raw.items():
        cluster_centers.setdefault(cluster_id, []).append(indexed[index][1])

    columns: list[BayColumn] = []
    labels: dict[int, int] = {}
    for cluster_id in sorted(cluster_centers.keys(), key=lambda cid: sum(cluster_centers[cid]) / len(cluster_centers[cid])):
        bay_id = len(columns) + 1
        center = sum(cluster_centers[cluster_id]) / len(cluster_centers[cluster_id])
        confidence = min(0.95, 0.55 + 0.08 * len(cluster_centers[cluster_id]))
        columns.append(BayColumn(id=bay_id, x_center=center, confidence=confidence))
        for index, mapped in raw.items():
            if mapped == cluster_id:
                labels[index] = bay_id

    return columns, labels
