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
        row = sorted(row, key=lambda item: (item["bbox"][0] + item["bbox"][2]) / 2.0)
        widths = [bbox_size(opening["bbox"])[0] for opening in row]
        heights = [bbox_size(opening["bbox"])[1] for opening in row]
        sills = [opening["bbox"][3] for opening in row]
        width_spread = (max(widths) - min(widths)) / max(median(widths), 1e-6)
        height_spread = (max(heights) - min(heights)) / max(median(heights), 1e-6)
        sill_spread = (max(sills) - min(sills)) / max(median(heights), 1e-6)
        constraints: list[str] = []
        supports: list[float] = []
        if width_spread <= 0.18:
            constraints.append("equal_width")
            supports.append(1.0 - width_spread)
        if height_spread <= 0.18:
            constraints.append("equal_height")
            supports.append(1.0 - height_spread)
        if sill_spread <= 0.15:
            constraints.extend(["equal_sill", "horizontal_alignment"])
            supports.append(1.0 - sill_spread)
        if len(row) >= 3:
            centers = [(item["bbox"][0] + item["bbox"][2]) / 2.0 for item in row]
            gaps = [centers[index + 1] - centers[index] for index in range(len(centers) - 1)]
            spacing_spread = (max(gaps) - min(gaps)) / max(median(gaps), 1e-6)
            if spacing_spread <= 0.20:
                constraints.append("equal_spacing")
                supports.append(1.0 - spacing_spread)
        constraints = list(dict.fromkeys(constraints))
        if constraints:
            groups.append(
                {
                    "id": f"storey_{storey}_row_pattern",
                    "members": [opening["id"] for opening in row if opening.get("id")],
                    "constraints": constraints,
                    "confidence": round(max(0.5, sum(supports) / len(supports)), 4),
                    "evidence": {
                        "width_spread": round(width_spread, 4),
                        "height_spread": round(height_spread, 4),
                        "sill_spread": round(sill_spread, 4),
                    },
                }
            )

    by_bay: dict[int, list[dict[str, Any]]] = {}
    for opening in openings:
        if opening.get("type") != "window" or opening.get("bay") is None:
            continue
        by_bay.setdefault(int(opening["bay"]), []).append(opening)
    for bay, column in sorted(by_bay.items()):
        if len(column) < 2:
            continue
        widths = [bbox_size(item["bbox"])[0] for item in column]
        centers = [(item["bbox"][0] + item["bbox"][2]) / 2.0 for item in column]
        width_spread = (max(widths) - min(widths)) / max(median(widths), 1e-6)
        center_spread = (max(centers) - min(centers)) / max(median(widths), 1e-6)
        constraints = []
        supports = []
        if width_spread <= 0.18:
            constraints.append("equal_width")
            supports.append(1.0 - width_spread)
        if center_spread <= 0.15:
            constraints.append("vertical_alignment")
            supports.append(1.0 - center_spread)
        if constraints:
            groups.append(
                {
                    "id": f"bay_{bay}_column_pattern",
                    "members": [item["id"] for item in column if item.get("id")],
                    "constraints": constraints,
                    "confidence": round(max(0.5, sum(supports) / len(supports)), 4),
                    "evidence": {
                        "width_spread": round(width_spread, 4),
                        "center_spread": round(center_spread, 4),
                    },
                }
            )
    return groups
