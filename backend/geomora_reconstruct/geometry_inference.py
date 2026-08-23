"""Facade-relative geometry ratios for openings."""
from __future__ import annotations

from typing import Any


def opening_geometry_ratios(
    opening: dict[str, Any],
    facade: dict[str, float],
    topology: dict[str, Any],
) -> dict[str, float]:
    x1, y1, x2, y2 = opening["bbox"]
    facade_width = float(facade.get("width", 1.0) or 1.0)
    facade_height = float(facade.get("height", 1.0) or 1.0)
    storeys = max(int(topology.get("storey_count", 1)), 1)
    storey_height = facade_height / storeys

    storey_index = int(opening.get("storey") or 1)
    storey_index = max(1, min(storey_index, storeys))
    storey_top = facade_height - (storey_index - 1) * storey_height
    storey_bottom = storey_top - storey_height

    sill_storey = (y2 - storey_bottom) / storey_height if storey_height > 0 else 0.0
    sill_storey = max(0.0, min(1.0, sill_storey))

    return {
        "width_facade": round((x2 - x1) / facade_width, 4),
        "height_storey": round((y2 - y1) / storey_height, 4),
        "sill_storey": round(sill_storey, 4),
    }


def attach_geometry_to_openings(
    openings: list[dict[str, Any]],
    facade: dict[str, float],
    topology: dict[str, Any],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for opening in openings:
        item = dict(opening)
        item["geometry"] = opening_geometry_ratios(item, facade, topology)
        enriched.append(item)
    return enriched


def summarize_geometry(openings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "method": "bbox_ratios_v0.1",
        "opening_count": len(openings),
    }
