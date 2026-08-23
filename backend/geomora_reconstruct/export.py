"""Export pipeline stages into Reconstruction Metrics v1 prediction format."""
from __future__ import annotations

from typing import Any

from geomora_detect.models import DetectionResult

from .geometry_inference import attach_geometry_to_openings, summarize_geometry
from .topology_inference import infer_topology_from_openings


def _normalize_facade_bounds(
    bounds: list[float] | list[int] | None,
    *,
    image_width: int,
    image_height: int,
) -> list[float] | None:
    if not bounds or len(bounds) < 4 or image_width <= 0 or image_height <= 0:
        return None
    x1, y1, x2, y2 = bounds
    return [
        round(x1 / image_width, 4),
        round(y1 / image_height, 4),
        round(x2 / image_width, 4),
        round(y2 / image_height, 4),
    ]


def detection_to_prediction(
    photo_id: str,
    detection: DetectionResult,
    *,
    topology: dict[str, Any] | None = None,
    infer_topology: bool = True,
    attach_geometry: bool = True,
    metric: dict[str, Any] | None = None,
    metric_anchors: list[dict[str, Any]] | None = None,
    rationalization_before: dict[str, float] | None = None,
    rationalization_after: dict[str, float] | None = None,
    sketchup: dict[str, bool] | None = None,
) -> dict[str, Any]:
    openings = []
    for index, element in enumerate(detection.elements, start=1):
        openings.append(
            {
                "id": f"pred_{index:03d}",
                "type": element.type,
                "bbox": [round(value, 4) for value in element.bbox_norm],
                "confidence": round(element.confidence, 4),
            }
        )

    facade_bounds = _normalize_facade_bounds(
        detection.debug.get("facade_bounds"),
        image_width=detection.image_width,
        image_height=detection.image_height,
    )
    facade = {"width": 1.0, "height": 1.0}
    if facade_bounds is not None:
        facade["bbox"] = facade_bounds

    topology_payload = topology
    if topology_payload is None and infer_topology and openings:
        topology_payload, openings = infer_topology_from_openings(
            openings,
            facade_bounds=facade_bounds,
        )

    geometry_payload = None
    if attach_geometry and openings and topology_payload is not None:
        openings = attach_geometry_to_openings(openings, facade, topology_payload)
        geometry_payload = summarize_geometry(openings)

    payload: dict[str, Any] = {
        "schema_version": "reconstruction-metrics-v1",
        "photo_id": photo_id,
        "facade": facade,
        "openings": openings,
        "pipeline": {
            "detection_method": detection.method,
            "detection_confidence": round(detection.confidence, 4),
            "scale_hint": detection.scale_hint,
        },
    }
    if topology_payload is not None:
        payload["topology"] = topology_payload
    if geometry_payload is not None:
        payload["geometry"] = geometry_payload
    if metric is not None:
        payload["metric"] = metric
        payload["metric_source"] = "explicit_metric"
    if metric_anchors is not None:
        payload["metric_anchors"] = [dict(anchor) for anchor in metric_anchors]
    if rationalization_before is not None:
        payload["rationalization_before"] = rationalization_before
    if rationalization_after is not None:
        payload["rationalization_after"] = rationalization_after
    if sketchup is not None:
        payload["sketchup"] = sketchup
    return payload
