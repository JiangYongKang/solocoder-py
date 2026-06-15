from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AggregationType(str, Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class OutputType(str, Enum):
    INTERMEDIATE = "intermediate"
    FINAL = "final"


@dataclass(frozen=True)
class Event:
    timestamp: float
    value: Any = None
    key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")


@dataclass(frozen=True)
class Window:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("window start must be non-negative")
        if self.end <= self.start:
            raise ValueError("window end must be greater than start")

    @property
    def size(self) -> float:
        return self.end - self.start

    def contains(self, timestamp: float) -> bool:
        return self.start <= timestamp < self.end


@dataclass
class WindowState:
    window: Window
    count: int = 0
    sum_value: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    is_fired: bool = False
    is_closed: bool = False
    final_output_emitted: bool = False

    def add(self, value: Any) -> None:
        numeric = float(value)
        self.count += 1
        self.sum_value += numeric
        if self.min_value is None or numeric < self.min_value:
            self.min_value = numeric
        if self.max_value is None or numeric > self.max_value:
            self.max_value = numeric

    def get_result(self, agg_type: AggregationType) -> Any:
        if not isinstance(agg_type, AggregationType):
            raise ValueError(f"Unknown aggregation type: {agg_type}")

        if self.count == 0:
            if agg_type == AggregationType.COUNT:
                return 0
            if agg_type in (AggregationType.SUM, AggregationType.AVG):
                return 0.0
            return None

        if agg_type == AggregationType.COUNT:
            return self.count
        elif agg_type == AggregationType.SUM:
            return self.sum_value
        elif agg_type == AggregationType.AVG:
            return self.sum_value / self.count
        elif agg_type == AggregationType.MIN:
            return self.min_value
        elif agg_type == AggregationType.MAX:
            return self.max_value
        else:
            raise ValueError(f"Unknown aggregation type: {agg_type}")


@dataclass(frozen=True)
class AggregationResult:
    window: Window
    agg_type: AggregationType
    value: Any
    output_type: OutputType
    is_late_update: bool = False

    @property
    def is_final(self) -> bool:
        return self.output_type == OutputType.FINAL

    @property
    def is_intermediate(self) -> bool:
        return self.output_type == OutputType.INTERMEDIATE
