from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional


_MAX_PURGE_PER_CALL = 100


@dataclass
class _CacheEntry:
    value: Any
    weight: int
    expire_at: Optional[float]


class LRUCache:
    def __init__(
        self,
        capacity: int = 128,
        max_weight: int = 1024,
        default_ttl: Optional[float] = None,
    ) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        if max_weight < 0:
            raise ValueError("max_weight must be non-negative")
        if default_ttl is not None and default_ttl < 0:
            raise ValueError("default_ttl must be non-negative")

        self._capacity = capacity
        self._max_weight = max_weight
        self._default_ttl = default_ttl
        self._store: OrderedDict[Any, _CacheEntry] = OrderedDict()
        self._current_weight: int = 0
        self._expirable_count: int = 0
        self._lock = threading.RLock()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def max_weight(self) -> int:
        return self._max_weight

    @property
    def current_weight(self) -> int:
        with self._lock:
            return self._current_weight

    @property
    def size(self) -> int:
        with self._lock:
            self._purge_expired()
            return len(self._store)

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expire_at is not None and entry.expire_at <= time.monotonic():
                self._store.pop(key)
                self._current_weight -= entry.weight
                self._expirable_count -= 1
                return None
            self._store.move_to_end(key)
            return entry.value

    def set(
        self,
        key: Any,
        value: Any,
        ttl: Optional[float] = None,
        weight: int = 1,
    ) -> None:
        if weight < 0:
            raise ValueError("weight must be non-negative")
        if ttl is not None and ttl < 0:
            raise ValueError("ttl must be non-negative")

        effective_ttl = ttl if ttl is not None else self._default_ttl
        expire_at = time.monotonic() + effective_ttl if effective_ttl is not None else None

        with self._lock:
            self._purge_expired()

            if self._max_weight > 0 and weight > self._max_weight:
                return

            if key in self._store:
                old_entry = self._store[key]
                self._current_weight -= old_entry.weight
                if old_entry.expire_at is not None:
                    self._expirable_count -= 1
                del self._store[key]

            self._store[key] = _CacheEntry(
                value=value,
                weight=weight,
                expire_at=expire_at,
            )
            self._store.move_to_end(key)
            self._current_weight += weight
            if expire_at is not None:
                self._expirable_count += 1

            self._evict_if_needed()

    def delete(self, key: Any) -> bool:
        with self._lock:
            self._purge_expired()
            if key in self._store:
                entry = self._store.pop(key)
                self._current_weight -= entry.weight
                if entry.expire_at is not None:
                    self._expirable_count -= 1
                return True
            return False

    def has(self, key: Any) -> bool:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.expire_at is not None and entry.expire_at <= time.monotonic():
                self._store.pop(key)
                self._current_weight -= entry.weight
                self._expirable_count -= 1
                return False
            return True

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._current_weight = 0
            self._expirable_count = 0

    def _purge_expired(self) -> None:
        if self._expirable_count == 0:
            return

        now = time.monotonic()
        expired_keys: list[Any] = []
        scanned = 0

        for key, entry in self._store.items():
            if scanned >= _MAX_PURGE_PER_CALL:
                break
            scanned += 1
            if entry.expire_at is not None and entry.expire_at <= now:
                expired_keys.append(key)

        for key in expired_keys:
            entry = self._store.pop(key)
            self._current_weight -= entry.weight
            self._expirable_count -= 1

    def _evict_if_needed(self) -> None:
        while self._capacity > 0 and len(self._store) > self._capacity:
            self._evict_lru()

        while self._max_weight > 0 and self._current_weight > self._max_weight:
            self._evict_lru()

    def _evict_lru(self) -> None:
        if not self._store:
            return
        oldest_key, oldest_entry = next(iter(self._store.items()))
        del self._store[oldest_key]
        self._current_weight -= oldest_entry.weight
        if oldest_entry.expire_at is not None:
            self._expirable_count -= 1
