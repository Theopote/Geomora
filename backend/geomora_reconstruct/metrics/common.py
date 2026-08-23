from __future__ import annotations

from collections.abc import Iterable


def mean(values: Iterable[float]) -> float | None:
    items = list(values)
    return sum(items) / len(items) if items else None


def rounded(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def relative_error(predicted: float, actual: float) -> float | None:
    if actual == 0:
        return None
    return abs(predicted - actual) / abs(actual)


def accuracy_from_error(error: float | None) -> float | None:
    return None if error is None else max(0.0, 1.0 - error)

