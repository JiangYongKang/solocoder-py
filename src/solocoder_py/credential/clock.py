from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        ...

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        ...


class RealClock(Clock):
    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


@dataclass
class ManualClock(Clock):
    _current_time: float = 0.0

    def now(self) -> float:
        return self._current_time

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("sleep duration must not be negative")
        self._current_time += seconds

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("advance duration must not be negative")
        self._current_time += seconds

    def set_time(self, timestamp: float) -> None:
        if timestamp < self._current_time:
            raise ValueError("cannot set time backwards")
        self._current_time = timestamp
