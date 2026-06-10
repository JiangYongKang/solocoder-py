from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import FrozenSet, Set

from .exceptions import InvalidWorkHoursError


@dataclass(frozen=True)
class WorkTimeRange:
    start: time
    end: time

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise InvalidWorkHoursError("Work time range start must be before end")

    @property
    def duration_hours(self) -> float:
        start_seconds = self.start.hour * 3600 + self.start.minute * 60 + self.start.second
        end_seconds = self.end.hour * 3600 + self.end.minute * 60 + self.end.second
        return (end_seconds - start_seconds) / 3600.0

    def contains(self, t: time) -> bool:
        return self.start <= t <= self.end


@dataclass
class WorkDaySchedule:
    morning: WorkTimeRange = field(default_factory=lambda: WorkTimeRange(time(9, 0), time(12, 0)))
    afternoon: WorkTimeRange = field(default_factory=lambda: WorkTimeRange(time(13, 0), time(18, 0)))

    @property
    def total_work_hours(self) -> float:
        return self.morning.duration_hours + self.afternoon.duration_hours

    def is_work_time(self, dt: datetime) -> bool:
        t = dt.time()
        return self.morning.contains(t) or self.afternoon.contains(t)

    def get_work_periods(self) -> list[WorkTimeRange]:
        return [self.morning, self.afternoon]


@dataclass
class CalendarConfig:
    holidays: FrozenSet[date] = field(default_factory=frozenset)
    workdays: FrozenSet[date] = field(default_factory=frozenset)
    work_schedule: WorkDaySchedule = field(default_factory=WorkDaySchedule)

    def __post_init__(self) -> None:
        conflicting = self.holidays & self.workdays
        if conflicting:
            raise ValueError(f"Dates cannot be both holiday and workday: {conflicting}")
