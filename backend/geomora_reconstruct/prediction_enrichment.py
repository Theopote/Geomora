"""Attach gate-evaluable blocks to a reconstruction prediction."""
from __future__ import annotations

from typing import Any

from geomora_detect.models import DetectionResult

from .ir_export import attach_metric_block, prediction_to_ir
from .rationalization_variance import attach_rationalization_metrics
from .sketchup_checks import attach_sketchup_checks


def enrich_prediction(
    prediction: dict[str, Any],
    detection: DetectionResult | None = None,
    *,
    attach_metric: bool = True,
    attach_rationalization: bool = True,
    attach_sketchup: bool = True,
    export_ir: bool = False,
) -> dict[str, Any]:
    if detection is not None:
        pipeline = dict(prediction.get("pipeline") or {})
        if detection.scale_hint and "scale_hint" not in pipeline:
            pipeline["scale_hint"] = detection.scale_hint
        prediction["pipeline"] = pipeline

    if attach_rationalization:
        attach_rationalization_metrics(prediction)
    if attach_metric:
        attach_metric_block(prediction)
    if attach_sketchup:
        attach_sketchup_checks(prediction)
    if export_ir:
        ir = prediction_to_ir(prediction)
        if ir is not None:
            prediction["architectural_ir"] = ir
    return prediction
