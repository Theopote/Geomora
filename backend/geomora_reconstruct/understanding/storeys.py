from __future__ import annotations

from .facade import bbox_center
from .openings import cluster_sorted
from .result import StoreyBand


def _band_center(band: StoreyBand) -> float:
    return (band.y_min + band.y_max) / 2.0


def merge_small_storey_clusters(
    bands: list[StoreyBand],
    labels: dict[int, int],
    *,
    min_members: int = 1,
) -> tuple[list[StoreyBand], dict[int, int]]:
    if len(bands) <= 1:
        return bands, labels

    member_counts: dict[int, int] = {}
    for cluster_id in labels.values():
        member_counts[cluster_id] = member_counts.get(cluster_id, 0) + 1

    small_ids = {band_id for band_id, count in member_counts.items() if count <= min_members}
    if not small_ids:
        return bands, labels

    band_by_id = {band.id: band for band in bands}
    updated_labels = dict(labels)
    large_bands = [band for band in bands if band.id not in small_ids]
    if not large_bands:
        return bands, labels

    for index, cluster_id in updated_labels.items():
        if cluster_id not in small_ids:
            continue
        center_y = _band_center(band_by_id[cluster_id])
        nearest = min(large_bands, key=lambda band: abs(_band_center(band) - center_y))
        updated_labels[index] = nearest.id

    surviving = sorted(large_bands, key=lambda band: -_band_center(band))
    remap = {band.id: storey_id for storey_id, band in enumerate(surviving, start=1)}
    final_bands = [
        StoreyBand(
            id=remap[band.id],
            y_min=band.y_min,
            y_max=band.y_max,
            confidence=band.confidence,
        )
        for band in surviving
    ]
    final_labels = {index: remap[cluster_id] for index, cluster_id in updated_labels.items()}
    final_bands.sort(key=lambda band: band.id)
    return final_bands, final_labels


def infer_storey_bands(
    windows: list[dict],
    *,
    tolerance: float,
) -> tuple[list[StoreyBand], dict[int, int]]:
    if not windows:
        return [], {}

    indexed = [(index, bbox_center(window["bbox"])[1]) for index, window in enumerate(windows)]
    raw = cluster_sorted(indexed, tolerance)
    cluster_values: dict[int, list[float]] = {}
    cluster_boxes: dict[int, list[list[float]]] = {}
    for index, cluster_id in raw.items():
        cluster_values.setdefault(cluster_id, []).append(indexed[index][1])
        cluster_boxes.setdefault(cluster_id, []).append(windows[index]["bbox"])

    mean_y = {cluster_id: sum(values) / len(values) for cluster_id, values in cluster_values.items()}
    order = sorted(mean_y.keys(), key=lambda cluster_id: -mean_y[cluster_id])
    remap = {cluster_id: storey_id for storey_id, cluster_id in enumerate(order, start=1)}

    bands: list[StoreyBand] = []
    labels: dict[int, int] = {}
    for cluster_id in order:
        storey_id = remap[cluster_id]
        boxes = cluster_boxes[cluster_id]
        y_min = min(box[1] for box in boxes)
        y_max = max(box[3] for box in boxes)
        confidence = min(0.95, 0.55 + 0.08 * len(boxes))
        bands.append(StoreyBand(id=storey_id, y_min=y_min, y_max=y_max, confidence=confidence))
        for index, mapped in raw.items():
            if mapped == cluster_id:
                labels[index] = storey_id

    bands.sort(key=lambda band: band.id)
    return merge_small_storey_clusters(bands, labels)
