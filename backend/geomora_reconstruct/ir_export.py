"""Export a minimal facade IR from reconstruction prediction."""
from __future__ import annotations

from typing import Any

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
) -> dict[str, float]:
    x1, y1, x2, y2 = opening["bbox"]
    storey_height_mm = wall_height_mm / max(storey_count, 1)
    storey_index = int(opening.get("storey") or 1)
    storey_index = max(1, min(storey_index, storey_count))
    storey_top = wall_height_mm - (storey_index - 1) * storey_height_mm
    sill_height = max(0.0, min(storey_top, (y2 - (storey_top - storey_height_mm))))
    return {
        "offset": round(x1 * wall_length_mm, 1),
        "width": round(max((x2 - x1) * wall_length_mm, 1.0), 1),
        "height": round(max((y2 - y1) * storey_height_mm, 1.0), 1),
        "sill_height": round(sill_height, 1),
    }


def prediction_to_ir(prediction: dict[str, Any]) -> dict[str, Any] | None:
    topology = prediction.get("topology") or {}
    openings = prediction.get("openings") or []
    scale_hint = prediction.get("pipeline", {}).get("scale_hint")
    metric = _scale_hint_to_metric(scale_hint)
    if metric is None:
        return None

    wall_length_mm = metric["facade_width_mm"]
    wall_height_mm = metric["facade_height_mm"]
    storey_count = max(int(topology.get("storey_count", 1) or 1), 1)
    storey_height_mm = wall_height_mm / storey_count

    ir_openings: list[dict[str, Any]] = []
    opening_ids_by_storey: dict[int, list[str]] = {}

    for index, opening in enumerate(openings, start=1):
        opening_id = opening.get("id") or f"opening_{index:03d}"
        geometry = _opening_mm(
            opening,
            wall_length_mm=wall_length_mm,
            wall_height_mm=wall_height_mm,
            storey_count=storey_count,
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
        "constraints": [],
        "metric": metric,
    }


def attach_metric_block(prediction: dict[str, Any]) -> dict[str, float] | None:
    scale_hint = prediction.get("pipeline", {}).get("scale_hint")
    topology = prediction.get("topology") or {}
    if scale_hint:
        scale_hint = {**scale_hint, "storey_count": topology.get("storey_count", 1)}
    metric = _scale_hint_to_metric(scale_hint)
    if metric is None:
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
    return metric
