from __future__ import annotations

import time
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        pass

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        pass


class RealClock(Clock):
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class ManualClock(Clock):
    def __init__(self, start_time: float = 0.0) -> None:
        self._current_time: float = start_time

    def now(self) -> float:
        return self._current_time

    def sleep(self, seconds: float) -> None:
        self._current_time += seconds

    def advance(self, seconds: float) -> None:
        self._current_time += seconds

    def set_time(self, t: float) -> None:
        self._current_time = t
