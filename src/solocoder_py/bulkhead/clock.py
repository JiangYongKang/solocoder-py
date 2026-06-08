from __future__ import annotations

import time
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        ...


class SystemClock(Clock):
    def now(self) -> float:
        return time.monotonic()


class ManualClock(Clock):
    def __init__(self, start_time: float = 0.0) -> None:
        self._current_time: float = start_time

    def now(self) -> float:
        return self._current_time

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot advance by negative seconds")
        self._current_time += seconds

    def set(self, time_value: float) -> None:
        self._current_time = time_value
