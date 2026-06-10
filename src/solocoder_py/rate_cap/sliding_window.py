from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, Tuple

from .clock import Clock, SystemClock


class SlidingWindowCounter:
    def __init__(
        self,
        window_seconds: float,
        max_operations: int,
        slide_granularity_seconds: float = 0.0,
        clock: Clock | None = None,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_operations <= 0:
            raise ValueError("max_operations must be positive")
        if slide_granularity_seconds < 0:
            raise ValueError("slide_granularity_seconds cannot be negative")
        if (
            slide_granularity_seconds > 0
            and slide_granularity_seconds > window_seconds
        ):
            raise ValueError(
                "slide_granularity_seconds cannot exceed window_seconds"
            )

        self._window_seconds: float = window_seconds
        self._max_operations: int = max_operations
        self._granularity: float = slide_granularity_seconds
        self._clock: Clock = clock or SystemClock()
        self._lock: threading.Lock = threading.Lock()
        self._last_observed_time: float = self._clock.now()

        if self._granularity > 0:
            self._buckets: Dict[int, int] = {}
            self._bucket_keys: Deque[int] = deque()
        else:
            self._timestamps: Deque[float] = deque()

    @property
    def window_seconds(self) -> float:
        return self._window_seconds

    @property
    def max_operations(self) -> int:
        return self._max_operations

    @property
    def slide_granularity_seconds(self) -> float:
        return self._granularity

    def _bucket_key(self, ts: float) -> int:
        return int(ts / self._granularity)

    def _check_clock_backward(self, current_time: float) -> None:
        if current_time < self._last_observed_time:
            if self._granularity > 0:
                self._buckets.clear()
                self._bucket_keys.clear()
            else:
                self._timestamps.clear()
        self._last_observed_time = current_time

    def _evict_expired_precise(self, current_time: float) -> None:
        cutoff = current_time - self._window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def _evict_expired_buckets(self, current_time: float) -> None:
        cutoff_bucket = self._bucket_key(current_time - self._window_seconds)
        while self._bucket_keys and self._bucket_keys[0] <= cutoff_bucket:
            old_key = self._bucket_keys.popleft()
            self._buckets.pop(old_key, None)

    def _count_precise(self, current_time: float) -> int:
        self._evict_expired_precise(current_time)
        return len(self._timestamps)

    def _count_buckets(self, current_time: float) -> int:
        self._evict_expired_buckets(current_time)
        return sum(self._buckets.values())

    def current_count(self) -> int:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            if self._granularity > 0:
                return self._count_buckets(current_time)
            else:
                return self._count_precise(current_time)

    def remaining(self) -> int:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            if self._granularity > 0:
                count = self._count_buckets(current_time)
            else:
                count = self._count_precise(current_time)
            return max(0, self._max_operations - count)

    def try_acquire(self, amount: int = 1) -> Tuple[bool, int, int]:
        if amount <= 0:
            raise ValueError("amount must be positive")
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)

            if self._granularity > 0:
                count = self._count_buckets(current_time)
            else:
                count = self._count_precise(current_time)

            if count + amount > self._max_operations:
                return (False, count, self._max_operations)

            if self._granularity > 0:
                key = self._bucket_key(current_time)
                if key not in self._buckets:
                    self._buckets[key] = 0
                    self._bucket_keys.append(key)
                self._buckets[key] += amount
            else:
                for _ in range(amount):
                    self._timestamps.append(current_time)

            return (True, count + amount, self._max_operations)

    def can_acquire(self, amount: int = 1) -> bool:
        if amount <= 0:
            raise ValueError("amount must be positive")
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            if self._granularity > 0:
                count = self._count_buckets(current_time)
            else:
                count = self._count_precise(current_time)
            return count + amount <= self._max_operations

    def _rollback_last(self, amount: int = 1) -> None:
        if amount <= 0:
            return
        with self._lock:
            if self._granularity > 0:
                remaining = amount
                while remaining > 0 and self._bucket_keys:
                    last_key = self._bucket_keys[-1]
                    bucket_count = self._buckets.get(last_key, 0)
                    if bucket_count <= remaining:
                        remaining -= bucket_count
                        self._buckets.pop(last_key, None)
                        self._bucket_keys.pop()
                    else:
                        self._buckets[last_key] = bucket_count - remaining
                        remaining = 0
            else:
                for _ in range(min(amount, len(self._timestamps))):
                    self._timestamps.pop()
