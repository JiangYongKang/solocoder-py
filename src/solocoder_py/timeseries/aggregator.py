from __future__ import annotations

import math
from typing import Iterable, Optional

from .exceptions import InvalidAggregationTypeError
from .models import AggregateValue, DataPoint


def align_timestamp(timestamp: float, window_seconds: int) -> float:
    return float(math.floor(timestamp / window_seconds) * window_seconds)


def aggregate_points(
    points: Iterable[DataPoint],
    window_seconds: int,
    agg_type: str,
) -> list[AggregateValue]:
    if agg_type not in {"avg", "max", "min", "sum", "count"}:
        raise InvalidAggregationTypeError(agg_type)
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")

    windows: dict[float, dict[str, dict]] = {}

    for point in points:
        window_start = align_timestamp(point.timestamp, window_seconds)
        labels_key = tuple(sorted(point.labels.items()))

        if window_start not in windows:
            windows[window_start] = {}
        if labels_key not in windows[window_start]:
            windows[window_start][labels_key] = {
                "sum": 0.0,
                "count": 0,
                "min": float("inf"),
                "max": float("-inf"),
                "labels": dict(labels_key),
            }

        state = windows[window_start][labels_key]
        state["sum"] += point.value
        state["count"] += 1
        if point.value < state["min"]:
            state["min"] = point.value
        if point.value > state["max"]:
            state["max"] = point.value

    result: list[AggregateValue] = []
    for window_start in sorted(windows.keys()):
        for labels_key in sorted(windows[window_start].keys()):
            state = windows[window_start][labels_key]
            result.append(
                AggregateValue(
                    timestamp=window_start,
                    avg=state["sum"] / state["count"],
                    max=state["max"],
                    min=state["min"],
                    sum=state["sum"],
                    count=state["count"],
                    labels=state["labels"],
                )
            )

    return result


def compute_aggregation(
    values: Iterable[float], agg_type: str
) -> Optional[float]:
    if agg_type not in {"avg", "max", "min", "sum", "count"}:
        raise InvalidAggregationTypeError(agg_type)

    values_list = list(values)
    if not values_list:
        return None

    if agg_type == "avg":
        return sum(values_list) / len(values_list)
    elif agg_type == "max":
        return max(values_list)
    elif agg_type == "min":
        return min(values_list)
    elif agg_type == "sum":
        return sum(values_list)
    elif agg_type == "count":
        return float(len(values_list))

    return None


__all__ = [
    "align_timestamp",
    "aggregate_points",
    "compute_aggregation",
]
