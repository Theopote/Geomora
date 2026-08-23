from __future__ import annotations

from typing import Any

from .common import mean, rounded


FIELDS = ("width_variance", "height_variance", "sill_variance", "spacing_variance", "alignment_deviation")


def evaluate_rationalization(prediction: dict[str, Any]) -> dict[str, Any] | None:
    before = prediction.get("rationalization_before")
    after = prediction.get("rationalization_after")
    if before is None or after is None:
        return None
    improvements = {
        field: (float(before[field]) - float(after[field])) / float(before[field])
        for field in FIELDS
        if field in before and field in after and float(before[field]) > 0
    }
    if not improvements:
        return None
    return {
        "before": {key: before[key] for key in FIELDS if key in before},
        "after": {key: after[key] for key in FIELDS if key in after},
        "improvement": {key: rounded(value) for key, value in improvements.items()},
        "mean_improvement": rounded(mean(improvements.values())),
    }

