from __future__ import annotations

import time
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        ...


class SystemClock(Clock):
    def now(self) -> float:
        return time.time()


class MockClock(Clock):
    def __init__(self, initial_time: float = 0.0) -> None:
        self._current_time = initial_time

    def now(self) -> float:
        return self._current_time

    def advance(self, seconds: float) -> None:
        self._current_time += seconds

    def set(self, timestamp: float) -> None:
        self._current_time = timestamp
