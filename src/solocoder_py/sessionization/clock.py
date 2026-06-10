from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        ...


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now()


class ManualClock(Clock):
    def __init__(self, start_time: datetime | None = None) -> None:
        self._current_time: datetime = start_time if start_time is not None else datetime.now()

    def now(self) -> datetime:
        return self._current_time

    def advance_seconds(self, seconds: float) -> None:
        from datetime import timedelta

        if seconds < 0:
            raise ValueError("Cannot advance by negative seconds")
        self._current_time += timedelta(seconds=seconds)

    def set(self, time_value: datetime) -> None:
        self._current_time = time_value
