from __future__ import annotations

from typing import Any

from .models import DetectedElement

STANDARD_DOOR_HEIGHT_MM = 2100.0
STANDARD_SILL_HEIGHT_MM = 900.0
STANDARD_WINDOW_HEIGHT_MM = 1500.0
FACADE_MARGIN_FACTOR = 0.88


def estimate_scale(
    elements: list[DetectedElement],
    image_width: int,
    image_height: int,
    facade_bounds: list[int] | None = None,
) -> dict[str, Any] | None:
    if not elements or image_width <= 0 or image_height <= 0:
        return None

    doors = [element for element in elements if element.type == "door"]
    windows = [element for element in elements if element.type == "window"]

    wall_height_mm = None
    height_method = None
    height_confidence = 0.0

    if doors:
        door = max(doors, key=lambda element: element.confidence)
        door_height_norm = door.bbox_norm[3] - door.bbox_norm[1]
        if door_height_norm >= 0.08:
            wall_height_mm = STANDARD_DOOR_HEIGHT_MM / door_height_norm
            height_method = "door_height"
            height_confidence = min(0.9, door.confidence)

    if wall_height_mm is None and windows:
        window = max(windows, key=lambda element: element.confidence)
        sill_norm = max(1.0 - window.bbox_norm[3], 0.05)
        wall_height_mm = STANDARD_SILL_HEIGHT_MM / sill_norm
        height_method = "window_sill"
        height_confidence = min(0.75, window.confidence)

        window_height_norm = window.bbox_norm[3] - window.bbox_norm[1]
        if window_height_norm >= 0.08:
            alt_height = STANDARD_WINDOW_HEIGHT_MM / window_height_norm
            if alt_height > wall_height_mm * 0.75 and alt_height < wall_height_mm * 1.35:
                wall_height_mm = (wall_height_mm + alt_height) / 2.0
                height_method = "window_sill_height_blend"
                height_confidence = min(0.8, window.confidence)

    if wall_height_mm is None:
        return None

    wall_height_mm = _snap_mm(wall_height_mm, 50.0)
    wall_height_mm = max(2400.0, min(6000.0, wall_height_mm))

    x_min = min(element.bbox_norm[0] for element in elements)
    x_max = max(element.bbox_norm[2] for element in elements)
    span_norm = max(x_max - x_min, 0.25)
    span_norm = _extrapolate_span_norm(
        span_norm,
        window_count=len(windows),
        facade_bounds=facade_bounds,
        image_width=image_width,
    )

    aspect = image_width / image_height
    wall_length_mm = (span_norm * wall_height_mm * aspect) / FACADE_MARGIN_FACTOR
    wall_length_mm = _snap_mm(wall_length_mm, 100.0)
    wall_length_mm = max(4000.0, min(30000.0, wall_length_mm))

    return {
        "wall_length_mm": round(wall_length_mm),
        "wall_height_mm": round(wall_height_mm),
        "method": height_method or "openings_span",
        "confidence": round(height_confidence or 0.6, 3),
        "opening_span_norm": round(span_norm, 4),
    }


def _extrapolate_span_norm(
    span_norm: float,
    *,
    window_count: int,
    facade_bounds: list[int] | None,
    image_width: int,
) -> float:
    adjusted = span_norm

    if facade_bounds and len(facade_bounds) >= 4 and image_width > 0:
        facade_span = (facade_bounds[2] - facade_bounds[0]) / image_width
        adjusted = max(adjusted, facade_span * 0.85)

    if window_count <= 2:
        adjusted = max(adjusted, 0.72)
    elif window_count <= 4:
        adjusted = max(adjusted, 0.58)

    return min(adjusted, 0.98)


def _snap_mm(value: float, grid: float) -> float:
    return round(value / grid) * grid
