"""Export pipeline stages into Reconstruction Metrics v1 prediction format."""
from __future__ import annotations

from typing import Any

from geomora_detect.models import DetectionResult

from .topology_inference import infer_topology_from_openings


def detection_to_prediction(
    photo_id: str,
    detection: DetectionResult,
    *,
    topology: dict[str, Any] | None = None,
    infer_topology: bool = True,
    metric: dict[str, Any] | None = None,
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

    topology_payload = topology
    if topology_payload is None and infer_topology and openings:
        topology_payload, openings = infer_topology_from_openings(openings)

    payload: dict[str, Any] = {
        "schema_version": "reconstruction-metrics-v1",
        "photo_id": photo_id,
        "facade": {"width": 1.0, "height": 1.0},
        "openings": openings,
        "pipeline": {
            "detection_method": detection.method,
            "detection_confidence": round(detection.confidence, 4),
            "scale_hint": detection.scale_hint,
        },
    }
    if topology_payload is not None:
        payload["topology"] = topology_payload
    if metric is not None:
        payload["metric"] = metric
    if rationalization_before is not None:
        payload["rationalization_before"] = rationalization_before
    if rationalization_after is not None:
        payload["rationalization_after"] = rationalization_after
    if sketchup is not None:
        payload["sketchup"] = sketchup
    return payload
