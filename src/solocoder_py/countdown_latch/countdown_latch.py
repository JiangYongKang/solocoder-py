from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from .exceptions import InvalidCountError, LatchTimeoutError
from .models import Clock, LatchState, LatchStats, SystemClock


_POLL_INTERVAL = 0.01


@dataclass
class CountdownLatch:
    count: int
    clock: Clock = field(default_factory=SystemClock)
    _current_count: int = field(init=False)
    _state: LatchState = field(init=False, default=LatchState.WAITING)
    _cond: threading.Condition = field(default_factory=threading.Condition)
    _waiting_threads: int = field(default=0)

    def __post_init__(self) -> None:
        if self.count < 0:
            raise InvalidCountError("count cannot be negative")
        self._current_count = self.count
        if self._current_count == 0:
            self._state = LatchState.OPENED

    @property
    def current_count(self) -> int:
        with self._cond:
            return self._current_count

    @property
    def is_open(self) -> bool:
        with self._cond:
            return self._state == LatchState.OPENED

    def count_down(self) -> None:
        with self._cond:
            if self._state == LatchState.OPENED:
                return
            self._current_count -= 1
            if self._current_count <= 0:
                self._current_count = 0
                self._state = LatchState.OPENED
                self._cond.notify_all()

    def wait(self, timeout: Optional[float] = None) -> None:
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be positive")

        deadline: Optional[float] = None
        if timeout is not None:
            deadline = self.clock.now() + timeout

        with self._cond:
            if self._state == LatchState.OPENED:
                return
            self._waiting_threads += 1

        try:
            while True:
                with self._cond:
                    if self._state == LatchState.OPENED:
                        return

                remaining: Optional[float] = None
                if deadline is not None:
                    remaining = deadline - self.clock.now()
                    if remaining <= 0:
                        raise LatchTimeoutError("Timed out waiting for latch to open")

                sleep_time = _POLL_INTERVAL if remaining is None else min(_POLL_INTERVAL, remaining)
                with self._cond:
                    if self._state == LatchState.OPENED:
                        return
                    self._cond.wait(timeout=sleep_time)
        finally:
            with self._cond:
                self._waiting_threads -= 1

    def get_stats(self) -> LatchStats:
        with self._cond:
            return LatchStats(
                initial_count=self.count,
                current_count=self._current_count,
                state=self._state,
                waiting_threads=self._waiting_threads,
            )
