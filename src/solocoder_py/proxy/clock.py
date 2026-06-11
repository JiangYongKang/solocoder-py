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
    def __init__(self, initial: float = 0.0) -> None:
        self._time = initial

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds

    def set(self, timestamp: float) -> None:
        self._time = timestamp
