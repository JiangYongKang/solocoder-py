from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from .exceptions import InvalidGranularityError, InvalidTimeRangeError


class Granularity(Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"

    @property
    def duration(self) -> timedelta:
        if self == Granularity.MINUTE:
            return timedelta(minutes=1)
        elif self == Granularity.HOUR:
            return timedelta(hours=1)
        elif self == Granularity.DAY:
            return timedelta(days=1)
        raise InvalidGranularityError(f"Unknown granularity: {self}")

    @property
    def order(self) -> int:
        if self == Granularity.MINUTE:
            return 0
        elif self == Granularity.HOUR:
            return 1
        elif self == Granularity.DAY:
            return 2
        raise InvalidGranularityError(f"Unknown granularity: {self}")

    @classmethod
    def from_order(cls, order: int) -> "Granularity":
        for g in cls:
            if g.order == order:
                return g
        raise InvalidGranularityError(f"Unknown granularity order: {order}")

    def is_finer_than(self, other: "Granularity") -> bool:
        return self.order < other.order

    def is_coarser_than(self, other: "Granularity") -> bool:
        return self.order > other.order


@dataclass(frozen=True)
class TimeWindow:
    granularity: Granularity
    start: datetime

    @property
    def end(self) -> datetime:
        return self.start + self.granularity.duration

    def contains(self, timestamp: datetime) -> bool:
        return self.start <= timestamp < self.end

    @property
    def key(self) -> tuple[str, float]:
        return (self.granularity.value, self.start.timestamp())

    def next_window(self) -> "TimeWindow":
        return TimeWindow(granularity=self.granularity, start=self.end)

    def previous_window(self) -> "TimeWindow":
        return TimeWindow(
            granularity=self.granularity,
            start=self.start - self.granularity.duration,
        )

    @classmethod
    def from_timestamp(cls, timestamp: datetime, granularity: Granularity) -> "TimeWindow":
        ts = timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

        if granularity == Granularity.MINUTE:
            start = ts.replace(second=0, microsecond=0)
        elif granularity == Granularity.HOUR:
            start = ts.replace(minute=0, second=0, microsecond=0)
        elif granularity == Granularity.DAY:
            start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            raise InvalidGranularityError(f"Unknown granularity: {granularity}")

        return cls(granularity=granularity, start=start)

    def to_coarser(self, coarser_granularity: Granularity) -> "TimeWindow":
        if not coarser_granularity.is_coarser_than(self.granularity):
            raise InvalidGranularityError(
                f"{coarser_granularity} is not coarser than {self.granularity}"
            )
        return TimeWindow.from_timestamp(self.start, coarser_granularity)


@dataclass
class Event:
    timestamp: datetime
    count: int = 1

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("count must be positive")
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class CountResult:
    window: TimeWindow
    count: int
    is_estimated: bool = False
    source_granularity: Optional[Granularity] = None


@dataclass
class GranularityConfig:
    retention: timedelta

    @classmethod
    def default(cls, granularity: Granularity) -> "GranularityConfig":
        if granularity == Granularity.MINUTE:
            return cls(retention=timedelta(hours=2))
        elif granularity == Granularity.HOUR:
            return cls(retention=timedelta(days=7))
        elif granularity == Granularity.DAY:
            return cls(retention=timedelta(days=90))
        raise InvalidGranularityError(f"Unknown granularity: {granularity}")


@dataclass
class WindowStore:
    _windows: dict[Granularity, dict[float, int]] = field(default_factory=lambda: {
        Granularity.MINUTE: {},
        Granularity.HOUR: {},
        Granularity.DAY: {},
    })

    def get_count(self, window: TimeWindow) -> Optional[int]:
        return self._windows[window.granularity].get(window.start.timestamp())

    def set_count(self, window: TimeWindow, count: int) -> None:
        self._windows[window.granularity][window.start.timestamp()] = count

    def increment(self, window: TimeWindow, delta: int = 1) -> int:
        key = window.start.timestamp()
        current = self._windows[window.granularity].get(key, 0)
        new_count = current + delta
        self._windows[window.granularity][key] = new_count
        return new_count

    def get_all_windows(self, granularity: Granularity) -> list[tuple[float, int]]:
        return sorted(self._windows[granularity].items())

    def remove_window(self, window: TimeWindow) -> None:
        self._windows[window.granularity].pop(window.start.timestamp(), None)

    def remove_windows_before(self, granularity: Granularity, cutoff: datetime) -> int:
        cutoff_ts = cutoff.timestamp()
        to_remove = [
            ts for ts in self._windows[granularity].keys() if ts < cutoff_ts
        ]
        for ts in to_remove:
            del self._windows[granularity][ts]
        return len(to_remove)

    def clear(self, granularity: Optional[Granularity] = None) -> None:
        if granularity is None:
            for g in Granularity:
                self._windows[g].clear()
        else:
            self._windows[granularity].clear()

    def count_windows(self, granularity: Granularity) -> int:
        return len(self._windows[granularity])


def validate_time_range(start: datetime, end: datetime) -> None:
    if start >= end:
        raise InvalidTimeRangeError("start time must be before end time")
