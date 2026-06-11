from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

from .exceptions import InvalidCapacityError
from .models import K, V


@dataclass
class _CacheEntry(Generic[V]):
    value: V


class LRUCache(Generic[K, V]):
    def __init__(self, capacity: int) -> None:
        if capacity < 0:
            raise InvalidCapacityError("capacity must be non-negative")

        self._capacity = capacity
        self._store: OrderedDict[K, _CacheEntry[V]] = OrderedDict()
        self._lock = threading.RLock()
        self._eviction_count: int = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def eviction_count(self) -> int:
        with self._lock:
            return self._eviction_count

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            self._store.move_to_end(key)
            return entry.value

    def set(self, key: K, value: V) -> None:
        with self._lock:
            if key in self._store:
                del self._store[key]

            self._store[key] = _CacheEntry(value=value)
            self._store.move_to_end(key)

            self._evict_if_needed()

    def delete(self, key: K) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def has(self, key: K) -> bool:
        with self._lock:
            return key in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._eviction_count = 0

    def _evict_if_needed(self) -> None:
        if self._capacity <= 0:
            return

        while len(self._store) > self._capacity:
            self._evict_lru()

    def _evict_lru(self) -> None:
        if not self._store:
            return

        oldest_key, _ = next(iter(self._store.items()))
        del self._store[oldest_key]
        self._eviction_count += 1
