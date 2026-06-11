from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from .exceptions import InvalidCountError, LatchTimeoutError
from .models import Clock, LatchState, LatchStats, SystemClock


@dataclass
class CountdownLatch:
    count: int
    clock: Clock = field(default_factory=SystemClock)
    _current_count: int = field(init=False)
    _state: LatchState = field(init=False, default=LatchState.WAITING)
    _event: threading.Event = field(default_factory=threading.Event)
    _mu: threading.Lock = field(default_factory=threading.Lock)
    _waiting_threads: int = field(default=0)

    def __post_init__(self) -> None:
        if self.count < 0:
            raise InvalidCountError("count cannot be negative")
        self._current_count = self.count
        if self._current_count == 0:
            self._state = LatchState.OPENED
            self._event.set()

    @property
    def current_count(self) -> int:
        with self._mu:
            return self._current_count

    @property
    def is_open(self) -> bool:
        with self._mu:
            return self._state == LatchState.OPENED

    def count_down(self) -> None:
        with self._mu:
            if self._state == LatchState.OPENED:
                return
            self._current_count -= 1
            if self._current_count <= 0:
                self._current_count = 0
                self._state = LatchState.OPENED
                self._event.set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be positive")

        with self._mu:
            if self._state == LatchState.OPENED:
                return True

        deadline: Optional[float] = None
        if timeout is not None:
            deadline = self.clock.now() + timeout

        while True:
            remaining: Optional[float] = None
            if deadline is not None:
                remaining = deadline - self.clock.now()
                if remaining <= 0:
                    return False

            with self._mu:
                self._waiting_threads += 1

            try:
                finished = self._event.wait(timeout=remaining)
            finally:
                with self._mu:
                    self._waiting_threads -= 1

            with self._mu:
                if self._state == LatchState.OPENED:
                    return True

            if not finished:
                return False

    def get_stats(self) -> LatchStats:
        with self._mu:
            return LatchStats(
                initial_count=self.count,
                current_count=self._current_count,
                state=self._state,
                waiting_threads=self._waiting_threads,
            )
