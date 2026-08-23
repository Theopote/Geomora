"""Understanding v0.1 — facade/storey/bay inference with outlier filtering."""

from __future__ import annotations

from typing import Any

from ..vlm_evidence import ArchitecturalEvidence
from .coordinator import coordinate_architectural_evidence

from .bays import infer_bay_columns
from .facade import bbox_center, infer_facade_bbox
from .openings import (
    adaptive_bay_tolerance,
    adaptive_storey_tolerance,
    partition_openings,
)
from .patterns import infer_pattern_groups
from .occlusions import infer_hidden_opening_hypotheses
from .doors import infer_door_storey_hypothesis
from .result import UnderstandingResult
from .storeys import infer_storey_hypotheses

def _nearest_storey(center_y: float, bands: list) -> int:
    if not bands:
        return 1
    return min(bands, key=lambda band: abs((band.y_min + band.y_max) / 2.0 - center_y)).id


def _nearest_bay(center_x: float, columns: list) -> int:
    if not columns:
        return 1
    return min(columns, key=lambda column: abs(column.x_center - center_x)).id


def understand_openings(
    openings: list[dict[str, Any]],
    *,
    facade_bounds: list[float] | None = None,
    architectural_evidence: ArchitecturalEvidence | None = None,
    storey_cues: list[dict[str, Any]] | None = None,
) -> tuple[UnderstandingResult, list[dict[str, Any]]]:
    result = UnderstandingResult()
    if not openings:
        result.uncertainties.append("no_openings")
        result.debug["storey_count"] = 1
        result.debug["bay_count"] = 1
        if architectural_evidence is not None:
            coordinate_architectural_evidence(result, architectural_evidence)
        return result, []

    facade_bbox = infer_facade_bbox(openings, facade_bounds)
    result.facade_bbox = facade_bbox

    core_pairs, outlier_pairs = partition_openings(openings, facade_bbox=facade_bbox)
    core_indices = {index for index, _opening in core_pairs}
    if outlier_pairs:
        result.uncertainties.append(f"filtered_outliers:{len(outlier_pairs)}")
        result.debug["outlier_ids"] = [openings[index].get("id") for index, _ in outlier_pairs]

    core_windows = [opening for index, opening in core_pairs if opening.get("type") == "window"]
    storey_tol = adaptive_storey_tolerance(core_windows)
    bay_tol = adaptive_bay_tolerance(core_windows)
    result.debug["storey_tolerance"] = round(storey_tol, 4)
    result.debug["bay_tolerance"] = round(bay_tol, 4)
    result.debug["core_window_count"] = len(core_windows)

    automatic_cues = list(storey_cues or [])
    for index, opening in core_pairs:
        if opening.get("type") != "door":
            continue
        door_hypothesis = infer_door_storey_hypothesis(
            opening, facade_bbox=facade_bbox, storeys=[],
            facade_bounds_observed=facade_bounds is not None,
        )
        if door_hypothesis["candidate_storey"] == 1 and any(
            item in door_hypothesis["evidence"]
            for item in ("near_observed_facade_bottom", "near_inferred_facade_bottom")
        ):
            automatic_cues.append({
                "id": f"door_baseline:{opening.get('id', index)}", "type": "door_baseline",
                "role": "door_baseline", "y": opening["bbox"][3],
                "confidence": door_hypothesis["confidence"], "source": "door_storey_hypothesis",
            })
    storeys, storey_labels, storey_audit = infer_storey_hypotheses(
        core_windows, tolerance=storey_tol, facade_bbox=facade_bbox, cues=automatic_cues,
    )
    bays, bay_labels = infer_bay_columns(core_windows, tolerance=bay_tol)
    result.storeys = storeys
    result.bays = bays
    result.debug["storey_hypothesis"] = storey_audit

    core_window_index = 0
    core_window_map: dict[int, int] = {}
    for index, opening in core_pairs:
        if opening.get("type") != "window":
            continue
        core_window_map[index] = core_window_index
        core_window_index += 1

    storey_by_index: dict[int, int] = {}
    bay_by_index: dict[int, int] = {}
    assignment_confidence: dict[int, float] = {}

    for global_index, opening in core_pairs:
        if opening.get("type") != "window":
            continue
        local_index = core_window_map[global_index]
        storey = storey_labels.get(local_index, 1)
        bay = bay_labels.get(local_index, 1)
        storey_by_index[global_index] = storey
        bay_by_index[global_index] = bay
        assignment_confidence[global_index] = min(
            next((band.confidence for band in storeys if band.id == storey), 0.6),
            next((column.confidence for column in bays if column.id == bay), 0.6),
        )

    for global_index, opening in core_pairs:
        if opening.get("type") != "door":
            continue
        hypothesis = infer_door_storey_hypothesis(
            opening, facade_bbox=facade_bbox, storeys=storeys,
            facade_bounds_observed=facade_bounds is not None,
        )
        storey_by_index[global_index] = hypothesis["candidate_storey"]
        bay_by_index[global_index] = _nearest_bay(bbox_center(opening["bbox"])[0], bays)
        assignment_confidence[global_index] = hypothesis["confidence"]

    for global_index, opening in outlier_pairs:
        center_x, center_y = bbox_center(opening["bbox"])
        storey_by_index[global_index] = _nearest_storey(center_y, storeys) if storeys else 1
        bay_by_index[global_index] = _nearest_bay(center_x, bays)
        assignment_confidence[global_index] = 0.35

    enriched: list[dict[str, Any]] = []
    for index, opening in enumerate(openings):
        item = dict(opening)
        if index in storey_by_index:
            item["storey"] = storey_by_index[index]
        if index in bay_by_index:
            item["bay"] = bay_by_index[index]
        confidence = assignment_confidence.get(index)
        if confidence is not None:
            item["assignment_confidence"] = round(confidence, 4)
            if confidence < 0.5:
                item["understanding_status"] = "low_confidence"
        enriched.append(item)

    result.pattern_groups = infer_pattern_groups(enriched)

    storey_count = len(storeys) if storeys else 1
    bay_count = len(bays) if bays else 1

    if storey_count <= 0:
        result.uncertainties.append("storey_count_zero")
    if len(core_windows) < 2:
        result.uncertainties.append("sparse_windows")

    result.debug["storey_count"] = int(storey_count)
    result.debug["bay_count"] = int(bay_count)
    result.debug["window_row_count"] = len(storeys)
    result.debug["window_column_count"] = len(bays)

    if architectural_evidence is not None:
        coordinate_architectural_evidence(result, architectural_evidence)

    if result.storeys:
        for item in enriched:
            if item.get("type") == "door" and item.get("bbox"):
                hypothesis = infer_door_storey_hypothesis(
                    item, facade_bbox=result.facade_bbox or facade_bbox, storeys=result.storeys,
                    facade_bounds_observed=facade_bounds is not None,
                )
                item["storey"] = hypothesis["candidate_storey"]
                item["storey_hypothesis"] = hypothesis
                item["assignment_confidence"] = hypothesis["confidence"]
                item["understanding_status"] = "hypothesized"
                result.door_hypotheses.append({"door_id": item.get("id"), **hypothesis})
            elif item.get("bbox"):
                item["storey"] = _nearest_storey(bbox_center(item["bbox"])[1], result.storeys)
    else:
        for item in enriched:
            if item.get("type") != "door" or not item.get("bbox"):
                continue
            hypothesis = infer_door_storey_hypothesis(
                item, facade_bbox=result.facade_bbox or facade_bbox, storeys=[],
                facade_bounds_observed=facade_bounds is not None,
            )
            item["storey"] = hypothesis["candidate_storey"]
            item["storey_hypothesis"] = hypothesis
            item["assignment_confidence"] = hypothesis["confidence"]
            item["understanding_status"] = "hypothesized"
            result.door_hypotheses.append({"door_id": item.get("id"), **hypothesis})

    if architectural_evidence is not None and architectural_evidence.occlusions:
        result.hidden_opening_hypotheses = infer_hidden_opening_hypotheses(
            enriched, architectural_evidence.occlusions,
        )
        result.debug["occlusion_awareness"] = {
            "occlusion_count": len(architectural_evidence.occlusions),
            "hidden_hypothesis_count": len(result.hidden_opening_hypotheses),
            "geometry_policy": "review_only_not_exported",
        }
        if result.hidden_opening_hypotheses:
            result.uncertainties.append(
                f"hidden_opening_hypotheses_require_confirmation:{len(result.hidden_opening_hypotheses)}"
            )

    return result, enriched


def understanding_to_topology(result: UnderstandingResult) -> dict[str, Any]:
    topology = {
        "storey_count": int(result.debug.get("storey_count", 1)),
        "bay_count": int(result.debug.get("bay_count", 1)),
        "method": result.method,
        "window_row_count": int(result.debug.get("window_row_count", 0)),
        "window_column_count": int(result.debug.get("window_column_count", 0)),
        "facade_bbox": result.facade_bbox,
        "storeys": [storey.to_dict() for storey in result.storeys],
        "bays": [bay.to_dict() for bay in result.bays],
        "pattern_groups": result.pattern_groups,
        "uncertainties": result.uncertainties,
        "storey_hypothesis": result.debug.get("storey_hypothesis", {}),
        "hidden_opening_hypotheses": result.hidden_opening_hypotheses,
        "occlusion_awareness": result.debug.get("occlusion_awareness", {}),
        "door_hypotheses": result.door_hypotheses,
    }
    if "evidence_coordination" in result.debug:
        topology["evidence_coordination"] = result.debug["evidence_coordination"]
    return topology
