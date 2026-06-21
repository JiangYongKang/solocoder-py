from __future__ import annotations

import functools
import inspect
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .exceptions import NotAFunctionError, UnhashableArgumentError


@dataclass
class _CacheEntry:
    value: Any
    created_at: float
    access_count: int = 0


@dataclass
class _CacheStats:
    total_accesses: int = 0
    hits: int = 0

    def reset(self) -> None:
        self.total_accesses = 0
        self.hits = 0

    @property
    def hit_rate(self) -> float:
        if self.total_accesses == 0:
            return 0.0
        return self.hits / self.total_accesses


class _MemoizeWrapper:
    def __init__(
        self,
        func: Callable[..., Any],
        ttl: float = 0,
        capacity: int = 128,
    ) -> None:
        if not (inspect.isfunction(func) or inspect.ismethod(func)):
            raise NotAFunctionError(func)

        self._func = func
        self._ttl = ttl
        self._capacity = capacity
        self._signature = inspect.signature(func)

        self._store: "OrderedDict[Any, _CacheEntry]" = OrderedDict()
        self._stats = _CacheStats()
        self._lock = threading.RLock()

        functools.update_wrapper(self, func)

    def _normalize_args(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[Any, ...]:
        bound = self._signature.bind(*args, **kwargs)
        bound.apply_defaults()

        normalized: list[Any] = []
        for name, value in bound.arguments.items():
            param = self._signature.parameters[name]
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                normalized.extend(value)
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                for k in sorted(value.keys()):
                    normalized.append((k, value[k]))
            else:
                normalized.append(value)

        return tuple(normalized)

    def _make_hashable(self, value: Any) -> Any:
        try:
            hash(value)
            return value
        except TypeError:
            pass

        if isinstance(value, list):
            return tuple(self._make_hashable(v) for v in value)
        elif isinstance(value, dict):
            return tuple(
                sorted((k, self._make_hashable(v)) for k, v in value.items())
            )
        elif isinstance(value, set):
            return frozenset(self._make_hashable(v) for v in value)
        else:
            raise UnhashableArgumentError("argument", value)

    def _generate_cache_key(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[Any, ...]:
        normalized = self._normalize_args(args, kwargs)
        try:
            hash(normalized)
            return normalized
        except TypeError:
            pass

        hashable_parts = []
        for i, value in enumerate(normalized):
            try:
                hash(value)
                hashable_parts.append(value)
            except TypeError:
                hashable_parts.append(self._make_hashable(value))
        return tuple(hashable_parts)

    def _is_expired(self, entry: _CacheEntry) -> bool:
        if self._ttl == 0:
            return False
        return (time.monotonic() - entry.created_at) > self._ttl

    def _evict_if_needed(self) -> None:
        while self._capacity > 0 and len(self._store) > self._capacity:
            self._store.popitem(last=False)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        cache_key = self._generate_cache_key(args, kwargs)

        with self._lock:
            self._stats.total_accesses += 1

            if cache_key in self._store:
                entry = self._store[cache_key]
                if not self._is_expired(entry):
                    self._store.move_to_end(cache_key)
                    entry.access_count += 1
                    self._stats.hits += 1
                    return entry.value
                else:
                    del self._store[cache_key]

            result = self._func(*args, **kwargs)

            self._store[cache_key] = _CacheEntry(
                value=result,
                created_at=time.monotonic(),
                access_count=1,
            )
            self._store.move_to_end(cache_key)

            self._evict_if_needed()

            return result

    def hit_rate(self) -> float:
        with self._lock:
            return self._stats.hit_rate

    def reset_stats(self) -> None:
        with self._lock:
            self._stats.reset()

    def cache_clear(self) -> None:
        with self._lock:
            self._store.clear()

    def cache_info(self) -> dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._store),
                "capacity": self._capacity,
                "ttl": self._ttl,
                "total_accesses": self._stats.total_accesses,
                "hits": self._stats.hits,
                "hit_rate": self._stats.hit_rate,
            }

    def __get__(self, instance: Any, owner: Optional[type] = None) -> Callable[..., Any]:
        if instance is None:
            return self
        bound_method = self._func.__get__(instance, owner)
        return _BoundMemoizeWrapper(self, bound_method, instance)


class _BoundMemoizeWrapper:
    def __init__(
        self,
        wrapper: _MemoizeWrapper,
        bound_method: Callable[..., Any],
        instance: Any,
    ) -> None:
        self._wrapper = wrapper
        self._bound_method = bound_method
        self._instance = instance
        functools.update_wrapper(self, bound_method)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrapper(self._instance, *args, **kwargs)

    def hit_rate(self) -> float:
        return self._wrapper.hit_rate()

    def reset_stats(self) -> None:
        self._wrapper.reset_stats()

    def cache_clear(self) -> None:
        self._wrapper.cache_clear()

    def cache_info(self) -> dict[str, Any]:
        return self._wrapper.cache_info()


def memoize(
    func: Optional[Callable[..., Any]] = None,
    *,
    ttl: float = 0,
    capacity: int = 128,
) -> Callable[..., Any]:
    if ttl < 0:
        raise ValueError("ttl must be non-negative")
    if capacity < 0:
        raise ValueError("capacity must be non-negative")

    def decorator(f: Callable[..., Any]) -> _MemoizeWrapper:
        return _MemoizeWrapper(f, ttl=ttl, capacity=capacity)

    if func is not None:
        return decorator(func)
    return decorator
