from __future__ import annotations

from geomora_detect.nms import iou

from .models import Observation, ObservationGraph, ObservationKind, ObservationSource


def _merge_semantics(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    keys = set(left) | set(right)
    return {key: max(left.get(key, 0.0), right.get(key, 0.0)) for key in keys}


def _merge_sources(left: list[ObservationSource], right: list[ObservationSource]) -> list[ObservationSource]:
    merged = list(left)
    seen = {(source.type, round(source.confidence, 4)) for source in left}
    for source in right:
        key = (source.type, round(source.confidence, 4))
        if key not in seen:
            merged.append(source)
            seen.add(key)
    return merged


def _can_merge(candidate: Observation, existing: Observation, iou_threshold: float) -> bool:
    if candidate.kind != existing.kind:
        return False
    if candidate.kind != ObservationKind.OPENING_CANDIDATE:
        return False
    bbox_a = candidate.geometry.get("bbox")
    bbox_b = existing.geometry.get("bbox")
    if not bbox_a or not bbox_b:
        return False
    return iou(bbox_a, bbox_b) >= iou_threshold


def _merge_pair(primary: Observation, secondary: Observation) -> Observation:
    confidence = max(primary.confidence, secondary.confidence)
    return Observation(
        id=primary.id,
        kind=primary.kind,
        geometry=primary.geometry,
        semantic_candidates=_merge_semantics(primary.semantic_candidates, secondary.semantic_candidates),
        confidence=confidence,
        sources=_merge_sources(primary.sources, secondary.sources),
        uncertainties=list(dict.fromkeys(primary.uncertainties + secondary.uncertainties)),
    )


def fuse_observation_graphs(
    *graphs: ObservationGraph,
    iou_threshold: float = 0.35,
) -> ObservationGraph:
    if not graphs:
        raise ValueError("at least one observation graph is required")

    photo_id = graphs[0].photo_id
    image_width = graphs[0].image_width
    image_height = graphs[0].image_height
    merged: list[Observation] = []
    counter = 0

    for graph in graphs:
        if graph.photo_id and graph.photo_id != photo_id:
            raise ValueError("all observation graphs must share the same photo_id")
        for candidate in graph.observations:
            match = None
            for index, existing in enumerate(merged):
                if _can_merge(candidate, existing, iou_threshold):
                    match = index
                    break
            if match is None:
                counter += 1
                merged.append(
                    Observation(
                        id=f"obs_fused_{counter:03d}",
                        kind=candidate.kind,
                        geometry=candidate.geometry,
                        semantic_candidates=dict(candidate.semantic_candidates),
                        confidence=candidate.confidence,
                        sources=list(candidate.sources),
                        uncertainties=list(candidate.uncertainties),
                    )
                )
            else:
                merged[match] = _merge_pair(merged[match], candidate)

    source_counts = {}
    for graph in graphs:
        adapter = graph.debug.get("adapter", "unknown")
        source_counts[adapter] = source_counts.get(adapter, 0) + len(graph.observations)

    return ObservationGraph(
        photo_id=photo_id,
        image_width=image_width,
        image_height=image_height,
        observations=merged,
        debug={
            "fusion": "observation_graph_v0.1",
            "source_graphs": len(graphs),
            "source_counts": source_counts,
            "fused_count": len(merged),
            "iou_threshold": iou_threshold,
        },
    )
