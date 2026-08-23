"""Deterministic reconstruction ablation stages and aggregation."""
from __future__ import annotations

from copy import deepcopy
from statistics import mean
from typing import Any

from geomora_detect.models import DetectionResult

from .export import detection_to_prediction
from .metrics import evaluate_reconstruction
from .prediction_enrichment import enrich_prediction
from .vlm_evidence import ArchitecturalEvidence

STAGES = (
    ("A_cv", "CV"),
    ("B_cv_vlm", "CV + VLM (raw evidence)"),
    ("C_understanding", "+ Understanding fusion"),
    ("D_metric_anchor", "+ Metric Anchor"),
    ("E_constraint_solver", "+ Constraint Solver"),
)


def _raw_vlm_topology(evidence: ArchitecturalEvidence) -> dict[str, Any]:
    return {
        "storey_count": int(evidence.visible_storeys.value),
        "bay_count": int(evidence.bay_count.value),
        "method": "vlm_raw_evidence_no_understanding",
        "facade_bbox": evidence.facade_bbox,
        "storeys": [], "bays": [], "pattern_groups": [],
        "uncertainties": list(evidence.uncertainties) + ["raw_vlm_topology_not_geometry_fused"],
    }


def build_stage_predictions(
    photo_id: str,
    detection: DetectionResult,
    *,
    evidence: ArchitecturalEvidence,
    metric_anchors: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    anchors = [dict(item) for item in (metric_anchors or [])]
    stage_a = detection_to_prediction(
        photo_id, detection, infer_topology=False, attach_geometry=False,
    )
    stage_b = detection_to_prediction(
        photo_id, detection, topology=_raw_vlm_topology(evidence),
        infer_topology=False, attach_geometry=False, architectural_evidence=evidence,
    )
    stage_c = detection_to_prediction(
        photo_id, detection, architectural_evidence=evidence,
    )
    stage_d = detection_to_prediction(
        photo_id, detection, metric_anchors=anchors, architectural_evidence=evidence,
    )
    enrich_prediction(
        stage_d, detection, attach_metric=True, attach_rationalization=False,
        attach_sketchup=False, export_ir=False, solve_constraints=False,
    )
    stage_e = deepcopy(stage_d)
    enrich_prediction(
        stage_e, detection, attach_metric=True, attach_rationalization=True,
        attach_sketchup=True, export_ir=True, solve_constraints=True,
    )
    return dict(zip((item[0] for item in STAGES), (stage_a, stage_b, stage_c, stage_d, stage_e)))


def build_vlm_pair_predictions(
    photo_id: str, detection: DetectionResult, *, evidence: ArchitecturalEvidence,
) -> dict[str, dict[str, Any]]:
    """Apples-to-apples VLM effect with Understanding enabled in both arms."""
    return {
        "without_vlm": detection_to_prediction(photo_id, detection),
        "with_vlm": detection_to_prediction(photo_id, detection, architectural_evidence=evidence),
    }


def _mean(values: list[float | None]) -> float | None:
    valid = [float(value) for value in values if value is not None]
    return round(mean(valid), 4) if valid else None


def summarize_stage(stage_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [row["metrics"] for row in rows]
    topology = [item.get("topology") or {} for item in metrics]
    geometry = [item.get("geometry") or {} for item in metrics]
    scale = [item.get("scale") or {} for item in metrics]
    solver = [item.get("constraint_solver") or {} for item in metrics]
    return {
        "stage": stage_id,
        "label": dict(STAGES)[stage_id],
        "photo_count": len(rows),
        "mean_rqs": _mean([item.get("rqs") for item in metrics]),
        "mean_coverage": _mean([item.get("coverage") for item in metrics]),
        "storey_accuracy": _mean([item.get("storey_accuracy") for item in topology]),
        "bay_accuracy": _mean([item.get("bay_accuracy") for item in topology]),
        "geometry_score": _mean([
            max(0.0, 1.0 - item["normalized_mae"]) if item.get("normalized_mae") is not None else None
            for item in geometry
        ]),
        "scale_score": _mean([
            max(0.0, 1.0 - item["mean_relative_error"]) if item.get("mean_relative_error") is not None else None
            for item in scale
        ]),
        "solver_pass_rate": _mean([
            1.0 if item.get("hard_constraints_satisfied") is True else 0.0
            if item.get("hard_constraints_satisfied") is False else None for item in solver
        ]),
        "results": rows,
    }


def summarize_vlm_pair(rows_by_arm: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    arms = {}
    for arm, rows in rows_by_arm.items():
        summary = summarize_stage("C_understanding", rows)
        arms[arm] = {key: value for key, value in summary.items() if key not in {"stage", "label", "results"}}
    metrics = ("mean_rqs", "mean_coverage", "storey_accuracy", "bay_accuracy", "geometry_score")
    delta = {
        key: round(arms["with_vlm"][key] - arms["without_vlm"][key], 4)
        if arms["with_vlm"].get(key) is not None and arms["without_vlm"].get(key) is not None else None
        for key in metrics
    }
    return {"comparison": "same_detection_same_understanding", "without_vlm": arms["without_vlm"],
            "with_vlm": arms["with_vlm"], "delta_with_minus_without": delta}


def evaluate_stages(
    truth: dict[str, Any], predictions: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {stage_id: evaluate_reconstruction(truth, prediction) for stage_id, prediction in predictions.items()}
