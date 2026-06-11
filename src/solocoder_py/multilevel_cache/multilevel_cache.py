from __future__ import annotations

import threading
from typing import Generic, Optional

from .exceptions import DataSourceError
from .lru_cache import LRUCache
from .models import CacheStats, DataSource, K, V, _MISSING, _MutableStats


class MultiLevelCache(Generic[K, V]):
    def __init__(
        self,
        l1_capacity: int,
        l2_capacity: int,
        data_source: Optional[DataSource[K, V]] = None,
    ) -> None:
        if l1_capacity <= 0:
            raise ValueError("l1_capacity must be positive")
        if l2_capacity <= 0:
            raise ValueError("l2_capacity must be positive")
        if l1_capacity >= l2_capacity:
            raise ValueError("l1_capacity must be less than l2_capacity")

        self._l1: LRUCache[K, V] = LRUCache(capacity=l1_capacity)
        self._l2: LRUCache[K, V] = LRUCache(capacity=l2_capacity)
        self._data_source = data_source
        self._lock = threading.RLock()

        self._stats = _MutableStats()

    @property
    def l1_capacity(self) -> int:
        return self._l1.capacity

    @property
    def l2_capacity(self) -> int:
        return self._l2.capacity

    @property
    def l1_size(self) -> int:
        return self._l1.size

    @property
    def l2_size(self) -> int:
        return self._l2.size

    @property
    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(
                l1_hits=self._stats.l1_hits,
                l2_hits=self._stats.l2_hits,
                l1_misses=self._stats.l1_misses,
                l2_misses=self._stats.l2_misses,
                data_source_loads=self._stats.data_source_loads,
                evictions_l1=self._l1.eviction_count,
                evictions_l2=self._l2.eviction_count,
            )

    def get(self, key: K) -> V:
        with self._lock:
            value = self._l1.get(key)
            if value is not _MISSING:
                self._stats.l1_hits += 1
                return value

            self._stats.l1_misses += 1

            value = self._l2.get(key)
            if value is not _MISSING:
                self._stats.l2_hits += 1
                self._l1.set(key, value)
                return value

            self._stats.l2_misses += 1

            if self._data_source is None:
                raise DataSourceError("No data source configured")

            try:
                value = self._data_source.load(key)
            except Exception as e:
                raise DataSourceError(f"Failed to load from data source: {e}") from e

            self._stats.data_source_loads += 1

            self._l2.set(key, value)
            self._l1.set(key, value)

            return value

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._l2.set(key, value)
            self._l1.set(key, value)

    def delete(self, key: K) -> bool:
        with self._lock:
            deleted_l1 = self._l1.delete(key)
            deleted_l2 = self._l2.delete(key)
            return deleted_l1 or deleted_l2

    def clear(self) -> None:
        with self._lock:
            self._l1.clear()
            self._l2.clear()
            self._stats.reset()

    def invalidate(self, key: K) -> None:
        self.delete(key)

    def has_in_l1(self, key: K) -> bool:
        return self._l1.has(key)

    def has_in_l2(self, key: K) -> bool:
        return self._l2.has(key)
