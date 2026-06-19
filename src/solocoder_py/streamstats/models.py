from dataclasses import dataclass
from typing import Optional


class StreamStatsError(Exception):
    pass


class InvalidValueError(StreamStatsError):
    def __init__(self, value: float, message: Optional[str] = None):
        self.value = value
        if message is None:
            message = f"Invalid value: {value} (NaN or Inf not allowed)"
        super().__init__(message)


class MergeError(StreamStatsError):
    pass


@dataclass(frozen=True)
class StatsResult:
    count: int
    mean: Optional[float]
    variance: Optional[float]
    skewness: Optional[float]
    kurtosis: Optional[float]
