from __future__ import annotations

import time
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        ...

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot sleep for negative seconds")
        self._do_sleep(seconds)

    def yield_cpu(self) -> None:
        pass

    @abstractmethod
    def _do_sleep(self, seconds: float) -> None:
        ...


class SystemClock(Clock):
    def now(self) -> float:
        return time.monotonic()

    def _do_sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class ManualClock(Clock):
    def __init__(self, start_time: float = 0.0) -> None:
        self._current_time: float = start_time
        self._sleep_history: list[float] = []

    def now(self) -> float:
        return self._current_time

    def _do_sleep(self, seconds: float) -> None:
        self._sleep_history.append(seconds)
        self._current_time += seconds

    def yield_cpu(self) -> None:
        time.sleep(0.001)

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot advance by negative seconds")
        self._current_time += seconds

    def set(self, time_value: float) -> None:
        self._current_time = time_value

    @property
    def sleep_history(self) -> list[float]:
        return list(self._sleep_history)
