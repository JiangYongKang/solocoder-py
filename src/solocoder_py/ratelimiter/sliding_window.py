from __future__ import annotations

import threading
from collections import deque
from typing import Deque

from .clock import Clock, SystemClock


class SlidingWindowRateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Clock | None = None,
    ) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self._max_requests: int = max_requests
        self._window_seconds: float = window_seconds
        self._clock: Clock = clock or SystemClock()
        self._timestamps: Deque[float] = deque()
        self._lock: threading.Lock = threading.Lock()
        self._last_observed_time: float = self._clock.now()

    @property
    def max_requests(self) -> int:
        return self._max_requests

    @property
    def window_seconds(self) -> float:
        return self._window_seconds

    def _check_clock_backward(self, current_time: float) -> None:
        if current_time < self._last_observed_time:
            self._timestamps.clear()
        self._last_observed_time = current_time

    def _evict_expired(self, current_time: float) -> None:
        cutoff = current_time - self._window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def try_acquire(self) -> bool:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            self._evict_expired(current_time)

            if len(self._timestamps) >= self._max_requests:
                return False

            self._timestamps.append(current_time)
            return True

    def can_acquire(self) -> bool:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            self._evict_expired(current_time)
            return len(self._timestamps) < self._max_requests

    def current_count(self) -> int:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            self._evict_expired(current_time)
            return len(self._timestamps)

    def _rollback_last(self) -> None:
        with self._lock:
            if self._timestamps:
                self._timestamps.pop()
