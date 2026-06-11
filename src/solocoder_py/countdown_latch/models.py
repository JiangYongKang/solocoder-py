from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import time


class LatchState(str, Enum):
    WAITING = "waiting"
    OPENED = "opened"


@dataclass
class LatchStats:
    initial_count: int
    current_count: int
    state: LatchState
    waiting_threads: int


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        pass


class SystemClock(Clock):
    def now(self) -> float:
        return time.monotonic()


class ManualClock(Clock):
    def __init__(self, start_time: float = 0.0) -> None:
        if start_time < 0:
            raise ValueError("start_time cannot be negative")
        self._time = start_time

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot advance by negative seconds")
        self._time += seconds

    def set(self, timestamp: float) -> None:
        if timestamp < 0:
            raise ValueError("timestamp cannot be negative")
        self._time = timestamp
