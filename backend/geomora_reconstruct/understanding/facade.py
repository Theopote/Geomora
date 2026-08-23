from __future__ import annotations

from typing import Any


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def bbox_size(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (max(x2 - x1, 0.0), max(y2 - y1, 0.0))


def infer_facade_bbox(
    openings: list[dict[str, Any]],
    facade_bounds: list[float] | None = None,
    *,
    margin: float = 0.02,
) -> list[float]:
    if facade_bounds and len(facade_bounds) >= 4:
        x1, y1, x2, y2 = facade_bounds
        return [
            max(0.0, x1 - margin),
            max(0.0, y1 - margin),
            min(1.0, x2 + margin),
            min(1.0, y2 + margin),
        ]

    if not openings:
        return [0.0, 0.0, 1.0, 1.0]

    x_min = min(opening["bbox"][0] for opening in openings)
    y_min = min(opening["bbox"][1] for opening in openings)
    x_max = max(opening["bbox"][2] for opening in openings)
    y_max = max(opening["bbox"][3] for opening in openings)
    pad_x = max((x_max - x_min) * 0.08, margin)
    pad_y = max((y_max - y_min) * 0.10, margin)
    return [
        max(0.0, x_min - pad_x),
        max(0.0, y_min - pad_y),
        min(1.0, x_max + pad_x),
        min(1.0, y_max + pad_y),
    ]
