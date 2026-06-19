from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float: ...


class RealClock:
    def now(self) -> float:
        return time.monotonic()


class ManualClock:
    def __init__(self, start_time: float = 0.0) -> None:
        self._time = start_time

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot advance by negative seconds")
        self._time += seconds

    def set_time(self, t: float) -> None:
        self._time = t
