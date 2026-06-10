from __future__ import annotations

import threading
from typing import Any, Optional

from .count_min_sketch import CountMinSketch
from .exceptions import InvalidCapacityError, InvalidKError
from .models import HeavyHitter


class HeavyHitterDetector:
    def __init__(
        self,
        capacity: int,
        epsilon: float = 0.001,
        delta: float = 0.99,
    ) -> None:
        if capacity <= 0:
            raise InvalidCapacityError("capacity must be a positive integer")

        self._capacity = capacity
        self._store: dict[Any, int] = {}
        self._cms = CountMinSketch(epsilon=epsilon, delta=delta)
        self._lock = threading.RLock()
        self._evicted_count: int = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def evicted_count(self) -> int:
        with self._lock:
            return self._evicted_count

    @property
    def total_items_processed(self) -> int:
        return self._cms.total_count

    def record(self, item: Any, count: int = 1) -> None:
        if count <= 0:
            raise ValueError("count must be positive")

        with self._lock:
            self._cms.add(item, count)

            if item in self._store:
                self._store[item] += count
                return

            if len(self._store) < self._capacity:
                self._store[item] = count
                return

            min_item, min_count = self._find_min_count_item()

            if count > min_count:
                del self._store[min_item]
                self._store[item] = count
                self._evicted_count += 1

    def estimate_count(self, item: Any) -> int:
        with self._lock:
            if item in self._store:
                return self._store[item]
            return self._cms.lower_bound(item)

    def lower_bound(self, item: Any) -> int:
        with self._lock:
            if item in self._store:
                return self._store[item]
            return self._cms.lower_bound(item)

    def upper_bound(self, item: Any) -> int:
        return self._cms.upper_bound(item)

    def contains(self, item: Any) -> bool:
        with self._lock:
            return item in self._store

    def get_top_k(self, k: int) -> list[HeavyHitter]:
        if k <= 0:
            raise InvalidKError("k must be a positive integer")
        if k > self._capacity:
            raise InvalidKError(
                f"k ({k}) cannot exceed capacity ({self._capacity})"
            )

        with self._lock:
            sorted_items = sorted(
                self._store.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            return [
                HeavyHitter(item=item, count=count)
                for item, count in sorted_items[:k]
            ]

    def get_all_tracked(self) -> list[HeavyHitter]:
        with self._lock:
            return [
                HeavyHitter(item=item, count=count)
                for item, count in sorted(
                    self._store.items(), key=lambda x: x[1], reverse=True
                )
            ]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._cms.clear()
            self._evicted_count = 0

    def merge(self, other: "HeavyHitterDetector") -> None:
        if other._capacity != self._capacity:
            raise ValueError(
                "Cannot merge detectors with different capacities"
            )

        with self._lock:
            with other._lock:
                self._cms.merge(other._cms)

                all_items = set(self._store.keys()) | set(other._store.keys())

                merged_store: dict[Any, int] = {}
                for item in all_items:
                    self_count = self._store.get(item, 0)
                    other_count = other._store.get(item, 0)
                    est = max(self_count, other_count, self._cms.lower_bound(item))
                    merged_store[item] = est

                if len(merged_store) > self._capacity:
                    sorted_items = sorted(
                        merged_store.items(), key=lambda x: x[1], reverse=True
                    )
                    self._store = dict(sorted_items[: self._capacity])
                    self._evicted_count += len(merged_store) - self._capacity
                else:
                    self._store = merged_store

    def _find_min_count_item(self) -> tuple[Any, int]:
        min_count: Optional[int] = None
        min_item: Any = None

        for item, count in self._store.items():
            if min_count is None or count < min_count:
                min_count = count
                min_item = item

        assert min_item is not None and min_count is not None
        return min_item, min_count
