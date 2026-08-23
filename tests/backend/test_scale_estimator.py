"""A2 scale span extrapolation tests."""

from __future__ import annotations

from geomora_detect.models import DetectedElement
from geomora_detect.scale_estimator import estimate_scale


def test_scale_extrapolates_span_with_few_windows():
    elements = [
        DetectedElement(type="window", bbox_norm=[0.35, 0.2, 0.45, 0.5], confidence=0.8),
        DetectedElement(type="window", bbox_norm=[0.55, 0.2, 0.65, 0.5], confidence=0.8),
    ]
    hint = estimate_scale(elements, 800, 600, facade_bounds=[40, 0, 760, 600])
    assert hint is not None
    assert hint["opening_span_norm"] >= 0.58
    assert hint["wall_length_mm"] >= 4000
