from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class DataPoint:
    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, (int, float)):
            raise ValueError("timestamp must be a number")
        if not isinstance(self.value, (int, float)):
            raise ValueError("value must be a number")
        if not isinstance(self.labels, dict):
            raise ValueError("labels must be a dict")
        for k, v in self.labels.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError("labels keys and values must be strings")

        object.__setattr__(self, "timestamp", float(self.timestamp))
        object.__setattr__(self, "value", float(self.value))

    @classmethod
    def from_datetime(
        cls,
        dt: datetime.datetime,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ) -> "DataPoint":
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return cls(
            timestamp=dt.timestamp(),
            value=float(value),
            labels=labels or {},
        )

    def to_datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.timestamp, tz=datetime.timezone.utc)


@dataclass
class AggregateValue:
    timestamp: float
    avg: float
    max: float
    min: float
    sum: float
    count: int
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("count must be non-negative")

    def get(self, agg_type: str) -> float:
        if agg_type == "avg":
            return self.avg
        elif agg_type == "max":
            return self.max
        elif agg_type == "min":
            return self.min
        elif agg_type == "sum":
            return self.sum
        elif agg_type == "count":
            return float(self.count)
        else:
            raise ValueError(f"Unsupported aggregation type: {agg_type}")


@dataclass
class Granularity:
    name: str
    window_seconds: int
    retention_seconds: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.retention_seconds is not None and self.retention_seconds <= 0:
            raise ValueError("retention_seconds must be positive or None")

    def align_timestamp(self, timestamp: float) -> float:
        return float(math.floor(timestamp / self.window_seconds) * self.window_seconds)


@dataclass
class RetentionPolicy:
    granularity_name: str
    retention_seconds: Optional[int]

    def __post_init__(self) -> None:
        if not self.granularity_name:
            raise ValueError("granularity_name must not be empty")
        if self.retention_seconds is not None and self.retention_seconds <= 0:
            raise ValueError("retention_seconds must be positive or None")


@dataclass
class RollupState:
    window_start: float
    sum: float = 0.0
    count: int = 0
    min: float = float("inf")
    max: float = float("-inf")

    def update(self, value: float) -> None:
        self.sum += value
        self.count += 1
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value

    def merge(self, other: "RollupState") -> None:
        self.sum += other.sum
        self.count += other.count
        if other.min < self.min:
            self.min = other.min
        if other.max > self.max:
            self.max = other.max

    def reset(self) -> None:
        self.sum = 0.0
        self.count = 0
        self.min = float("inf")
        self.max = float("-inf")

    def rebuild_from_values(self, values: list[float]) -> None:
        self.reset()
        for v in values:
            self.update(v)

    def to_aggregate(
        self, labels: Optional[dict[str, str]] = None
    ) -> Optional[AggregateValue]:
        if self.count == 0:
            return None
        return AggregateValue(
            timestamp=self.window_start,
            avg=self.sum / self.count,
            max=self.max,
            min=self.min,
            sum=self.sum,
            count=self.count,
            labels=labels or {},
        )


@dataclass
class QueryOptions:
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    labels: Optional[dict[str, str]] = None
    agg_type: Optional[str] = None

    def __post_init__(self) -> None:
        if self.agg_type is not None and self.agg_type not in {
            "avg",
            "max",
            "min",
            "sum",
            "count",
        }:
            raise ValueError(f"Unsupported agg_type: {self.agg_type}")


__all__ = [
    "DataPoint",
    "AggregateValue",
    "Granularity",
    "RetentionPolicy",
    "RollupState",
    "QueryOptions",
]
