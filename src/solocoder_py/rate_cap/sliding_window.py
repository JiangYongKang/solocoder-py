from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, Optional, Tuple

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
            self._bucket_totals: Dict[int, int] = {}
            self._bucket_by_tag: Dict[int, Dict[Optional[str], int]] = {}
            self._bucket_keys: Deque[int] = deque()
        else:
            self._timestamps: Deque[float] = deque()
            self._tags: Deque[Optional[str]] = deque()

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
            self._clear_unlocked()
        self._last_observed_time = current_time

    def _clear_unlocked(self) -> None:
        if self._granularity > 0:
            self._bucket_totals.clear()
            self._bucket_by_tag.clear()
            self._bucket_keys.clear()
        else:
            self._timestamps.clear()
            self._tags.clear()

    def clear(self) -> None:
        with self._lock:
            self._clear_unlocked()

    def _evict_expired_precise(self, current_time: float) -> None:
        cutoff = current_time - self._window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()
            self._tags.popleft()

    def _evict_expired_buckets(self, current_time: float) -> None:
        cutoff_bucket = self._bucket_key(current_time - self._window_seconds)
        while self._bucket_keys and self._bucket_keys[0] <= cutoff_bucket:
            old_key = self._bucket_keys.popleft()
            self._bucket_totals.pop(old_key, None)
            self._bucket_by_tag.pop(old_key, None)

    def _count_precise(self, current_time: float) -> int:
        self._evict_expired_precise(current_time)
        return len(self._timestamps)

    def _count_buckets(self, current_time: float) -> int:
        self._evict_expired_buckets(current_time)
        return sum(self._bucket_totals.values())

    def current_count(self) -> int:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            if self._granularity > 0:
                return self._count_buckets(current_time)
            else:
                return self._count_precise(current_time)

    def count_by_tag(self, tag: Optional[str]) -> int:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            if self._granularity > 0:
                self._evict_expired_buckets(current_time)
                total = 0
                for per_tag in self._bucket_by_tag.values():
                    total += per_tag.get(tag, 0)
                return total
            else:
                self._evict_expired_precise(current_time)
                count = 0
                for t in self._tags:
                    if t == tag:
                        count += 1
                return count

    def remaining(self) -> int:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            if self._granularity > 0:
                count = self._count_buckets(current_time)
            else:
                count = self._count_precise(current_time)
            return max(0, self._max_operations - count)

    def try_acquire(
        self,
        amount: int = 1,
        tag: Optional[str] = None,
    ) -> Tuple[bool, int, int]:
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
                if key not in self._bucket_totals:
                    self._bucket_totals[key] = 0
                    self._bucket_by_tag[key] = {}
                    self._bucket_keys.append(key)
                self._bucket_totals[key] += amount
                per_tag = self._bucket_by_tag[key]
                per_tag[tag] = per_tag.get(tag, 0) + amount
            else:
                for _ in range(amount):
                    self._timestamps.append(current_time)
                    self._tags.append(tag)

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
                    bucket_total = self._bucket_totals.get(last_key, 0)
                    if bucket_total <= remaining:
                        remaining -= bucket_total
                        self._bucket_totals.pop(last_key, None)
                        self._bucket_by_tag.pop(last_key, None)
                        self._bucket_keys.pop()
                    else:
                        self._bucket_totals[last_key] = bucket_total - remaining
                        per_tag = self._bucket_by_tag[last_key]
                        to_remove = remaining
                        tags_in_order = list(reversed(list(per_tag.keys())))
                        for t in tags_in_order:
                            if to_remove <= 0:
                                break
                            tag_count = per_tag.get(t, 0)
                            if tag_count <= to_remove:
                                to_remove -= tag_count
                                per_tag.pop(t, None)
                            else:
                                per_tag[t] = tag_count - to_remove
                                to_remove = 0
                        remaining = 0
            else:
                actual = min(amount, len(self._timestamps))
                for _ in range(actual):
                    self._timestamps.pop()
                    self._tags.pop()

    def remove_by_tag(
        self,
        tag: Optional[str],
        amount: Optional[int] = None,
    ) -> int:
        if amount is not None and amount <= 0:
            return 0
        removed_total = 0
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)

            if self._granularity > 0:
                self._evict_expired_buckets(current_time)
                remaining = amount
                for bucket_key in list(self._bucket_keys):
                    if remaining is not None and remaining <= 0:
                        break
                    per_tag = self._bucket_by_tag.get(bucket_key)
                    if per_tag is None:
                        continue
                    tag_count = per_tag.get(tag, 0)
                    if tag_count == 0:
                        continue
                    to_remove = tag_count if remaining is None else min(tag_count, remaining)
                    per_tag[tag] = tag_count - to_remove
                    if per_tag[tag] == 0:
                        per_tag.pop(tag, None)
                    self._bucket_totals[bucket_key] -= to_remove
                    removed_total += to_remove
                    if remaining is not None:
                        remaining -= to_remove
                    if self._bucket_totals[bucket_key] == 0:
                        self._bucket_totals.pop(bucket_key, None)
                        self._bucket_by_tag.pop(bucket_key, None)
                        if bucket_key in self._bucket_keys:
                            idx = self._bucket_keys.index(bucket_key)
                            del self._bucket_keys[idx]
            else:
                self._evict_expired_precise(current_time)
                new_ts: Deque[float] = deque()
                new_tags: Deque[Optional[str]] = deque()
                remaining = amount
                for i in range(len(self._timestamps)):
                    ts = self._timestamps[i]
                    t = self._tags[i]
                    if t == tag and (remaining is None or remaining > 0):
                        removed_total += 1
                        if remaining is not None:
                            remaining -= 1
                    else:
                        new_ts.append(ts)
                        new_tags.append(t)
                self._timestamps = new_ts
                self._tags = new_tags

        return removed_total
