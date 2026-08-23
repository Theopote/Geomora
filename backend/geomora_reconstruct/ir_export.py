"""Export a minimal facade IR from reconstruction prediction."""
from __future__ import annotations

from typing import Any

from .metric_anchors import derive_metric_from_anchors

DEFAULT_WALL_THICKNESS_MM = 240.0


def _scale_hint_to_metric(scale_hint: dict[str, Any] | None) -> dict[str, float] | None:
    if not scale_hint:
        return None
    wall_length = scale_hint.get("wall_length_mm")
    wall_height = scale_hint.get("wall_height_mm")
    if wall_length is None or wall_height is None:
        return None
    storeys = max(int(scale_hint.get("storey_count", 1) or 1), 1)
    return {
        "facade_width_mm": float(wall_length),
        "facade_height_mm": float(wall_height),
        "storey_height_mm": float(wall_height) / storeys,
    }


def _opening_mm(
    opening: dict[str, Any],
    *,
    wall_length_mm: float,
    wall_height_mm: float,
    storey_count: int,
    facade_bbox: list[float] | None = None,
) -> dict[str, float]:
    x1, y1, x2, y2 = opening["bbox"]
    fx1, fy1, fx2, fy2 = facade_bbox or [0.0, 0.0, 1.0, 1.0]
    facade_width_norm = max(fx2 - fx1, 1e-6)
    facade_height_norm = max(fy2 - fy1, 1e-6)
    nx1 = max(0.0, min(1.0, (x1 - fx1) / facade_width_norm))
    nx2 = max(0.0, min(1.0, (x2 - fx1) / facade_width_norm))
    ny1 = max(0.0, min(1.0, (y1 - fy1) / facade_height_norm))
    ny2 = max(0.0, min(1.0, (y2 - fy1) / facade_height_norm))
    storey_height_mm = wall_height_mm / max(storey_count, 1)
    storey_index = int(opening.get("storey") or 1)
    storey_index = max(1, min(storey_index, storey_count))
    height_mm = max((ny2 - ny1) * wall_height_mm, 1.0)
    opening_bottom_elevation = (1.0 - ny2) * wall_height_mm
    storey_base_elevation = (storey_index - 1) * storey_height_mm
    sill_height = opening_bottom_elevation - storey_base_elevation
    sill_height = max(0.0, min(storey_height_mm - height_mm, sill_height))
    return {
        "offset": round(nx1 * wall_length_mm, 1),
        "width": round(max((nx2 - nx1) * wall_length_mm, 1.0), 1),
        "height": round(height_mm, 1),
        "sill_height": round(sill_height, 1),
    }


def resolve_prediction_metric(prediction: dict[str, Any]) -> tuple[dict[str, float] | None, str | None]:
    """Resolve dimensions in hard-to-weak priority order.

    User/survey anchors are hard evidence. An explicitly supplied metric block
    comes next, while detector scale hints remain a weak fallback.
    """
    topology = prediction.get("topology") or {}
    scale_hint = prediction.get("pipeline", {}).get("scale_hint")
    if scale_hint:
        scale_hint = {**scale_hint, "storey_count": topology.get("storey_count", 1)}
    fallback = _scale_hint_to_metric(scale_hint) or {}
    explicit = prediction.get("metric")
    if explicit:
        fallback.update({key: float(value) for key, value in explicit.items()})
    anchored = derive_metric_from_anchors(
        prediction.get("metric_anchors") or [],
        topology=topology,
    ) or {}
    fallback.update(anchored)
    if not fallback:
        return None, None
    storey_count = int(topology.get("storey_count") or 0)
    if fallback.get("facade_height_mm") and storey_count > 0:
        fallback["storey_height_mm"] = fallback["facade_height_mm"] / storey_count
    if anchored:
        required = {"facade_width_mm", "facade_height_mm"}
        source = "metric_anchor" if required.issubset(anchored) else "metric_anchor_blended"
    elif explicit:
        source = prediction.get("metric_source", "explicit_metric")
    else:
        source = "scale_hint"
    return fallback, source


def prediction_to_ir(prediction: dict[str, Any]) -> dict[str, Any] | None:
    topology = prediction.get("topology") or {}
    openings = prediction.get("openings") or []
    metric, metric_source = resolve_prediction_metric(prediction)
    if metric is None:
        return None

    wall_length_mm = metric["facade_width_mm"]
    wall_height_mm = metric["facade_height_mm"]
    storey_count = max(int(topology.get("storey_count", 1) or 1), 1)
    storey_height_mm = wall_height_mm / storey_count
    facade_bbox = topology.get("facade_bbox") or prediction.get("facade", {}).get("bbox")

    ir_openings: list[dict[str, Any]] = []
    opening_ids_by_storey: dict[int, list[str]] = {}

    for index, opening in enumerate(openings, start=1):
        opening_id = opening.get("id") or f"opening_{index:03d}"
        geometry = _opening_mm(
            opening,
            wall_length_mm=wall_length_mm,
            wall_height_mm=wall_height_mm,
            storey_count=storey_count,
            facade_bbox=facade_bbox,
        )
        storey_index = int(opening.get("storey") or 1)
        parent_id = f"wall_{storey_index:02d}_01"
        ir_openings.append(
            {
                "id": opening_id,
                "type": opening.get("type", "window"),
                "parent_id": parent_id,
                "geometry": {
                    **geometry,
                    "depth": DEFAULT_WALL_THICKNESS_MM,
                },
                "confidence": opening.get("confidence", 0.5),
            }
        )
        opening_ids_by_storey.setdefault(storey_index, []).append(opening_id)

    storeys: list[dict[str, Any]] = []
    for storey_index in range(1, storey_count + 1):
        wall_id = f"wall_{storey_index:02d}_01"
        elevation = (storey_index - 1) * storey_height_mm
        storeys.append(
            {
                "id": f"storey_{storey_index:02d}",
                "name": f"Storey {storey_index}",
                "elevation": round(elevation, 1),
                "height": round(storey_height_mm, 1),
                "elements": [
                    {
                        "id": wall_id,
                        "type": "wall",
                        "storey_id": f"storey_{storey_index:02d}",
                        "geometry": {
                            "baseline": [[0, 0, elevation], [wall_length_mm, 0, elevation]],
                            "height": storey_height_mm,
                            "thickness": DEFAULT_WALL_THICKNESS_MM,
                        },
                        "semantic": {"exterior": True},
                        "opening_ids": opening_ids_by_storey.get(storey_index, []),
                        "confidence": 0.8,
                    }
                ],
            }
        )

    return {
        "schema_version": "0.1",
        "project": {
            "id": f"project_{prediction.get('photo_id', 'unknown')}",
            "name": prediction.get("photo_id", "Reconstruction"),
            "unit": "mm",
            "coordinate_system": "z_up",
            "default_wall_thickness": DEFAULT_WALL_THICKNESS_MM,
        },
        "buildings": [
            {
                "id": "building_001",
                "name": "Main Building",
                "storeys": storeys,
            }
        ],
        "openings": ir_openings,
        "constraints": [
            dict(item)
            for item in prediction.get("constraint_suggestions", [])
            if item.get("status", "proposed") == "proposed"
        ],
        "metric": metric,
        "metric_source": metric_source,
    }


def attach_metric_block(prediction: dict[str, Any]) -> dict[str, float] | None:
    metric, metric_source = resolve_prediction_metric(prediction)
    if metric is None or "facade_width_mm" not in metric or "facade_height_mm" not in metric:
        return None
    windows = [opening for opening in prediction.get("openings", []) if opening.get("type") == "window"]
    if windows:
        sample = max(windows, key=lambda item: item.get("confidence", 0.0))
        geometry = sample.get("geometry") or {}
        if geometry.get("width_facade") and metric.get("facade_width_mm"):
            metric["window_width_mm"] = round(geometry["width_facade"] * metric["facade_width_mm"], 1)
        if geometry.get("height_storey") and metric.get("storey_height_mm"):
            metric["window_height_mm"] = round(geometry["height_storey"] * metric["storey_height_mm"], 1)
    prediction["metric"] = metric
    prediction["metric_source"] = metric_source
    return metric
