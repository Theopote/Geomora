"""Rule-based storey/bay inference from opening detections."""
from __future__ import annotations

from typing import Any

DEFAULT_STOREY_TOLERANCE = 0.08
DEFAULT_BAY_TOLERANCE = 0.10
DOOR_FLOOR_Y_MIN = 0.72


def _bbox_center(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _cluster_sorted(values: list[tuple[int, float]], tolerance: float) -> dict[int, int]:
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


def _infer_storey_labels(
    windows: list[dict[str, Any]],
    *,
    tolerance: float = DEFAULT_STOREY_TOLERANCE,
) -> dict[int, int]:
    if not windows:
        return {}

    indexed = [(index, _bbox_center(window["bbox"])[1]) for index, window in enumerate(windows)]
    raw = _cluster_sorted(indexed, tolerance)
    cluster_means: dict[int, list[float]] = {}
    for index, cluster_id in raw.items():
        cluster_means.setdefault(cluster_id, []).append(indexed[index][1])

    mean_y = {cluster_id: sum(values) / len(values) for cluster_id, values in cluster_means.items()}
    order = sorted(mean_y.keys(), key=lambda cluster_id: -mean_y[cluster_id])
    remap = {cluster_id: storey for storey, cluster_id in enumerate(order, start=1)}
    return {index: remap[raw[index]] for index in raw}


def _infer_bay_labels(
    windows: list[dict[str, Any]],
    *,
    tolerance: float = DEFAULT_BAY_TOLERANCE,
) -> dict[int, int]:
    if not windows:
        return {}

    indexed = [(index, _bbox_center(window["bbox"])[0]) for index, window in enumerate(windows)]
    return _cluster_sorted(indexed, tolerance)


def _nearest_bay(center_x: float, bay_centers: dict[int, float]) -> int:
    if not bay_centers:
        return 1
    return min(bay_centers.keys(), key=lambda bay: abs(bay_centers[bay] - center_x))


def infer_topology_from_openings(
    openings: list[dict[str, Any]],
    *,
    storey_tolerance: float = DEFAULT_STOREY_TOLERANCE,
    bay_tolerance: float = DEFAULT_BAY_TOLERANCE,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not openings:
        return {"storey_count": 1, "bay_count": 1, "method": "cluster_v0.1"}, []

    windows = [(index, opening) for index, opening in enumerate(openings) if opening.get("type") == "window"]
    doors = [(index, opening) for index, opening in enumerate(openings) if opening.get("type") == "door"]

    storey_by_index: dict[int, int] = {}
    bay_by_index: dict[int, int] = {}

    window_storey: dict[int, int] = {}
    window_bay: dict[int, int] = {}
    if windows:
        window_list = [opening for _, opening in windows]
        window_storey = _infer_storey_labels(window_list, tolerance=storey_tolerance)
        window_bay = _infer_bay_labels(window_list, tolerance=bay_tolerance)
        for local_index, (global_index, _) in enumerate(windows):
            storey_by_index[global_index] = window_storey.get(local_index, 1)
            bay_by_index[global_index] = window_bay.get(local_index, 1)

    bay_centers: dict[int, float] = {}
    if windows:
        for local_index, (_, opening) in enumerate(windows):
            bay = window_bay.get(local_index, 1)
            center_x = _bbox_center(opening["bbox"])[0]
            values = bay_centers.setdefault(bay, [])
            values.append(center_x)
        bay_centers = {bay: sum(values) / len(values) for bay, values in bay_centers.items()}

    max_window_storey = max(window_storey.values()) if window_storey else 0
    for global_index, door in doors:
        bbox = door["bbox"]
        if bbox[3] >= DOOR_FLOOR_Y_MIN:
            storey_by_index[global_index] = 1
        else:
            storey_by_index[global_index] = max(max_window_storey, 1)
        bay_by_index[global_index] = _nearest_bay(_bbox_center(bbox)[0], bay_centers)

    enriched: list[dict[str, Any]] = []
    for index, opening in enumerate(openings):
        item = dict(opening)
        if index in storey_by_index:
            item["storey"] = storey_by_index[index]
        if index in bay_by_index:
            item["bay"] = bay_by_index[index]
        enriched.append(item)

    storey_count = max(storey_by_index.values()) if storey_by_index else 1
    window_bays = [bay_by_index[index] for index, opening in enumerate(openings) if opening.get("type") == "window"]
    bay_count = max(window_bays) if window_bays else 1

    topology = {
        "storey_count": int(storey_count),
        "bay_count": int(bay_count),
        "method": "cluster_v0.1",
        "window_row_count": len(set(window_storey.values())) if window_storey else 0,
        "window_column_count": len(set(window_bay.values())) if window_bay else 0,
    }
    return topology, enriched
