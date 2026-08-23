"""Production reconstruction orchestration shared by API and benchmarks."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from geomora_detect.pipeline import detect_facade

from .export import detection_to_prediction
from .observations.adapters import detection_result_to_observations
from .prediction_enrichment import enrich_prediction


def reconstruct_facade(
    image_path: str | Path,
    *,
    photo_id: str,
    method: str = "auto",
    metric: dict[str, float] | None = None,
    metric_anchors: list[dict[str, Any]] | None = None,
    return_overlay: bool = True,
) -> dict[str, Any]:
    """Turn one facade image into evidence, understanding and editable IR.

    This is deliberately provider-neutral. Detectors emit observations; the
    understanding/constraint layers decide which architectural facts reach IR.
    """
    detection = detect_facade(str(image_path), method=method, return_overlay=return_overlay)
    observation_graph = detection_result_to_observations(
        detection,
        photo_id=photo_id,
    )
    prediction = detection_to_prediction(
        photo_id,
        detection,
        metric=metric,
        metric_anchors=metric_anchors or [],
    )
    enrich_prediction(prediction, detection, export_ir=True)

    topology = prediction.get("topology") or {}
    openings = prediction.get("openings") or []
    uncertainties = list(topology.get("uncertainties") or [])
    solution = prediction.get("constraint_solution") or {}
    safety_status = solution.get("safety_status", "not_run")
    review_required = bool(uncertainties) or safety_status in {
        "accepted_after_soft_weight_retry",
        "fallback_observed_geometry",
    }

    return {
        "schema_version": "geomora-reconstruction-v0.1",
        "photo_id": photo_id,
        "status": "ready" if prediction.get("architectural_ir") else "needs_metric_scale",
        "detection": detection.to_dict(),
        "observation_graph": observation_graph.to_dict(),
        "understanding": {
            "method": topology.get("method", "understanding_v0.1"),
            "storey_count": topology.get("storey_count", 0),
            "bay_count": topology.get("bay_count", 0),
            "opening_count": len(openings),
            "facade_bbox": topology.get("facade_bbox"),
            "storeys": topology.get("storeys") or [],
            "bays": topology.get("bays") or [],
            "uncertain_openings": [
                {"id": item.get("id"), "bbox": item.get("bbox")}
                for item in openings
                if item.get("understanding_status") == "low_confidence"
            ],
            "uncertainties": uncertainties,
        },
        "constraint_solution": solution or None,
        "prediction": prediction,
        "architectural_ir": prediction.get("architectural_ir"),
        "review_required": review_required,
    }
