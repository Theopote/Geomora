from __future__ import annotations

from statistics import median
from typing import Any

from .facade import bbox_size


def infer_pattern_groups(openings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_storey: dict[int, list[dict[str, Any]]] = {}
    for opening in openings:
        if opening.get("type") != "window":
            continue
        storey = int(opening.get("storey") or 1)
        by_storey.setdefault(storey, []).append(opening)

    for storey, row in sorted(by_storey.items()):
        if len(row) < 2:
            continue
        widths = [bbox_size(opening["bbox"])[0] for opening in row]
        width_spread = (max(widths) - min(widths)) / max(median(widths), 1e-6)
        if width_spread <= 0.18:
            groups.append(
                {
                    "id": f"storey_{storey}_equal_width",
                    "members": [opening["id"] for opening in row if opening.get("id")],
                    "constraints": ["equal_width", "horizontal_alignment"],
                    "confidence": round(max(0.5, 1.0 - width_spread), 4),
                }
            )
    return groups
