from __future__ import annotations

from .facade import bbox_center
from .openings import cluster_sorted
from .result import StoreyBand

BOUNDARY_ROLES = {"storey_boundary", "floor_slab", "balcony_slab", "depth_discontinuity"}


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
            evidence=list(band.evidence),
            status=band.status,
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
        member_ids = [windows[index].get("id") for index, mapped in raw.items() if mapped == cluster_id]
        bands.append(StoreyBand(
            id=storey_id, y_min=y_min, y_max=y_max, confidence=confidence,
            evidence=[{"type": "window_row", "members": member_ids, "confidence": round(confidence, 4)}],
        ))
        for index, mapped in raw.items():
            if mapped == cluster_id:
                labels[index] = storey_id

    bands.sort(key=lambda band: band.id)
    return merge_small_storey_clusters(bands, labels)


def infer_storey_hypotheses(
    windows: list[dict], *, tolerance: float, facade_bbox: list[float],
    cues: list[dict] | None = None,
) -> tuple[list[StoreyBand], dict[int, int], dict]:
    """Fuse evidence conservatively; generic horizontal lines cannot create floors."""
    bands, labels = infer_storey_bands(windows, tolerance=tolerance)
    valid_cues = []
    for index, cue in enumerate(cues or []):
        try:
            y = float(cue["y"])
            confidence = max(0.0, min(1.0, float(cue.get("confidence", 0.5))))
        except (KeyError, TypeError, ValueError):
            continue
        valid_cues.append({
            "id": str(cue.get("id", f"storey_cue_{index + 1:03d}")),
            "role": str(cue.get("role", cue.get("type", "horizontal_structure"))),
            "y": y, "confidence": confidence,
            "source": str(cue.get("source", "observation_layer")),
        })

    boundaries = [cue for cue in valid_cues if cue["role"] in BOUNDARY_ROLES and cue["confidence"] >= 0.7]
    if not bands and boundaries:
        top, bottom = float(facade_bbox[1]), float(facade_bbox[3])
        ys = [top] + sorted({cue["y"] for cue in boundaries if top + 0.04 < cue["y"] < bottom - 0.04}) + [bottom]
        if len(ys) >= 3:
            for storey_id, (y_min, y_max) in enumerate(reversed(list(zip(ys[:-1], ys[1:]))), start=1):
                supporting = [cue for cue in boundaries if abs(cue["y"] - y_min) <= 0.015 or abs(cue["y"] - y_max) <= 0.015]
                bands.append(StoreyBand(
                    storey_id, y_min, y_max, min(0.85, 0.45 + 0.2 * len(supporting)),
                    status="hypothesized",
                ))

    used_ids: set[str] = set()
    for band in bands:
        for cue in valid_cues:
            if min(abs(cue["y"] - band.y_min), abs(cue["y"] - band.y_max)) > 0.035:
                continue
            used_ids.add(cue["id"])
            band.evidence.append({
                "type": cue["role"], "id": cue["id"], "source": cue["source"],
                "y": round(cue["y"], 4), "confidence": round(cue["confidence"], 4),
            })
            band.confidence = min(0.98, 1.0 - (1.0 - band.confidence) * (1.0 - 0.35 * cue["confidence"]))

    return bands, labels, {
        "model": "architectural_storey_hypothesis_v0.1", "cue_count": len(valid_cues),
        "boundary_cue_count": len(boundaries), "used_cue_ids": sorted(used_ids),
        "unused_cue_ids": sorted(cue["id"] for cue in valid_cues if cue["id"] not in used_ids),
    }
