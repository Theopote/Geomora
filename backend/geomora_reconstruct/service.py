"""Production reconstruction orchestration shared by API and benchmarks."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from geomora_detect.pipeline import detect_facade
from geomora_detect.image_io import imread_bgr
from geomora_multiview.depth import compute_depth_map

from .export import detection_to_prediction
from .observations.adapters import detection_result_to_observations
from .observations.vlm_adapter import vlm_evidence_to_observations
from .observations.models import ObservationKind
from .observations.structural_lines import (
    detect_horizontal_structure_observations,
    horizontal_observations_to_storey_cues,
    classify_horizontal_structure_roles,
)
from .observations.depth_discontinuities import (
    depth_discontinuity_observations,
    depth_observations_to_storey_cues,
)
from .prediction_enrichment import enrich_prediction
from .vlm_evidence import provider_api_key, request_architectural_evidence
from geomora_detect.vlm_prelabel import default_model, sanitize_error_message


def reconstruct_facade(
    image_path: str | Path,
    *,
    photo_id: str,
    method: str = "auto",
    metric: dict[str, float] | None = None,
    metric_anchors: list[dict[str, Any]] | None = None,
    return_overlay: bool = True,
    routing_mode: str = "local_only",
    vlm_provider: str = "openai",
    vlm_model: str = "auto",
    cloud_upload_authorized: bool = False,
    depth_method: str = "off",
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
    facade_observation = next(
        (item for item in observation_graph.observations if item.kind == ObservationKind.FACADE_CANDIDATE),
        None,
    )
    facade_bbox = facade_observation.geometry.get("bbox") if facade_observation else None
    storey_cues: list[dict[str, Any]] = []
    try:
        line_graph = detect_horizontal_structure_observations(
            image_path, photo_id=photo_id, facade_bbox=facade_bbox,
        )
        detected_openings = [
            {"type": element.type, "bbox": list(element.bbox_norm), "confidence": element.confidence}
            for element in detection.elements
        ]
        role_counts = classify_horizontal_structure_roles(
            line_graph.observations, openings=detected_openings, facade_bbox=facade_bbox,
        )
        line_graph.debug["role_counts"] = role_counts
        line_graph.debug["semantic_classifier"] = "opening_context_v0.1"
        observation_graph.observations.extend(line_graph.observations)
        observation_graph.debug["horizontal_structure"] = line_graph.debug
        storey_cues = horizontal_observations_to_storey_cues(line_graph.observations)
    except (ValueError, cv2.error) as error:
        observation_graph.debug["horizontal_structure"] = {
            "adapter": "horizontal_structure_v0.1", "status": "failed", "error": str(error),
        }
    depth_evidence = {"requested": depth_method not in {"", "off", "none"}, "used": False}
    if depth_evidence["requested"]:
        try:
            depth_map, resolved_depth_method = compute_depth_map(imread_bgr(image_path), method=depth_method)
            depth_graph = depth_discontinuity_observations(
                depth_map, photo_id=photo_id, method=resolved_depth_method, facade_bbox=facade_bbox,
            )
            observation_graph.observations.extend(depth_graph.observations)
            observation_graph.debug["depth_discontinuity"] = depth_graph.debug
            storey_cues.extend(depth_observations_to_storey_cues(depth_graph.observations))
            depth_evidence.update({"used": True, "method": resolved_depth_method,
                                   "candidate_count": len(depth_graph.observations),
                                   "metric_depth_evidence": depth_graph.debug["metric_depth_evidence"]})
        except (ValueError, RuntimeError, cv2.error) as error:
            depth_evidence.update({"status": "failed", "error": str(error)})
            observation_graph.debug["depth_discontinuity"] = depth_evidence
    cloud = {"requested": routing_mode == "cloud_enhanced", "used": False, "provider": vlm_provider}
    architectural_evidence = None
    if routing_mode == "cloud_enhanced":
        if not cloud_upload_authorized:
            cloud["status"] = "authorization_required"
        else:
            key = provider_api_key(vlm_provider)
            if not key:
                cloud["status"] = "provider_not_configured"
            else:
                active_model = default_model(vlm_provider) if vlm_model in {"", "auto"} else vlm_model
                try:
                    architectural_evidence = request_architectural_evidence(Path(image_path), photo_id=photo_id, provider=vlm_provider, model=active_model, api_key=key)
                    vlm_graph = vlm_evidence_to_observations(architectural_evidence, image_width=detection.image_width, image_height=detection.image_height)
                    observation_graph.observations.extend(vlm_graph.observations)
                    observation_graph.debug["vlm_evidence_count"] = len(vlm_graph.observations)
                    cloud.update({"used": True, "status": "completed", "model": active_model})
                except Exception as error:  # noqa: BLE001 - local reconstruction must survive cloud failure
                    cloud.update({"status": "failed", "error": sanitize_error_message(str(error), key)})
    prediction = detection_to_prediction(
        photo_id,
        detection,
        metric=metric,
        metric_anchors=metric_anchors or [],
        architectural_evidence=architectural_evidence,
        storey_cues=storey_cues,
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
            "evidence_coordination": topology.get("evidence_coordination"),
        },
        "constraint_solution": solution or None,
        "prediction": prediction,
        "architectural_ir": prediction.get("architectural_ir"),
        "review_required": review_required,
        "cloud_evidence": cloud,
        "depth_evidence": depth_evidence,
    }
