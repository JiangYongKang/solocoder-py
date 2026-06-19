from __future__ import annotations

import threading
from bisect import bisect_left
from typing import Mapping, Optional, Sequence

from .exceptions import InvalidBoundariesError, InvalidOperationError


class Labels:
    def __init__(self, labels: Optional[Mapping[str, str]] = None) -> None:
        if labels is None:
            labels = {}
        self._labels: dict[str, str] = dict(labels)

    @property
    def frozen(self) -> "FrozenLabels":
        return FrozenLabels(self._labels)

    def items(self):
        return self._labels.items()

    def keys(self):
        return self._labels.keys()

    def values(self):
        return self._labels.values()

    def to_dict(self) -> dict[str, str]:
        return dict(self._labels)

    def __getitem__(self, key: str) -> str:
        return self._labels[key]

    def __contains__(self, key: str) -> bool:
        return key in self._labels

    def __len__(self) -> int:
        return len(self._labels)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Labels):
            return NotImplemented
        return self._labels == other._labels

    def __hash__(self) -> int:
        return hash(tuple(sorted(self._labels.items())))

    def __repr__(self) -> str:
        return f"Labels({self._labels!r})"


class FrozenLabels:
    def __init__(self, labels: Optional[Mapping[str, str]] = None) -> None:
        if labels is None:
            labels = {}
        self._labels: dict[str, str] = dict(labels)
        self._hash: int = hash(tuple(sorted(self._labels.items())))

    @property
    def labels(self) -> dict[str, str]:
        return dict(self._labels)

    def matches(self, query: Mapping[str, str]) -> bool:
        for k, v in query.items():
            if self._labels.get(k) != v:
                return False
        return True

    def has_keys(self, keys: set[str]) -> bool:
        return all(k in self._labels for k in keys)

    def to_dict(self) -> dict[str, str]:
        return dict(self._labels)

    def items(self):
        return self._labels.items()

    def keys(self):
        return self._labels.keys()

    def values(self):
        return self._labels.values()

    def __getitem__(self, key: str) -> str:
        return self._labels[key]

    def __contains__(self, key: str) -> bool:
        return key in self._labels

    def __len__(self) -> int:
        return len(self._labels)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FrozenLabels):
            return NotImplemented
        return self._labels == other._labels

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return f"FrozenLabels({self._labels!r})"


class Counter:
    def __init__(self, name: str, help_text: str = "", labels: Optional[Mapping[str, str]] = None) -> None:
        self._name = name
        self._help = help_text
        self._labels = FrozenLabels(labels)
        self._value: float = 0.0
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def help(self) -> str:
        return self._help

    @property
    def labels(self) -> FrozenLabels:
        return self._labels

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def inc(self, delta: float = 1.0) -> None:
        if delta < 0:
            raise InvalidOperationError("Counter cannot be decremented")
        with self._lock:
            self._value += delta

    def dec(self, delta: float = 1.0) -> None:
        raise InvalidOperationError("Counter does not support dec operation")

    def observe(self, value: float) -> None:
        raise InvalidOperationError("Counter does not support observe operation")


class Gauge:
    def __init__(self, name: str, help_text: str = "", labels: Optional[Mapping[str, str]] = None) -> None:
        self._name = name
        self._help = help_text
        self._labels = FrozenLabels(labels)
        self._value: float = 0.0
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def help(self) -> str:
        return self._help

    @property
    def labels(self) -> FrozenLabels:
        return self._labels

    @property
    def value(self) -> float:
        with self._lock:
            return self._value

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def inc(self, delta: float = 1.0) -> None:
        with self._lock:
            self._value += delta

    def dec(self, delta: float = 1.0) -> None:
        with self._lock:
            self._value -= delta

    def observe(self, value: float) -> None:
        raise InvalidOperationError("Gauge does not support observe operation")


class Histogram:
    def __init__(
        self,
        name: str,
        buckets: Sequence[float],
        help_text: str = "",
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._validate_buckets(buckets)
        self._name = name
        self._help = help_text
        self._labels = FrozenLabels(labels)
        self._buckets: list[float] = sorted(float(b) for b in buckets)
        self._bucket_counts: list[int] = [0] * (len(self._buckets) + 1)
        self._sum: float = 0.0
        self._count: int = 0
        self._lock = threading.RLock()

    @staticmethod
    def _validate_buckets(buckets: Sequence[float]) -> None:
        if buckets is None or len(buckets) == 0:
            raise InvalidBoundariesError("Histogram buckets cannot be empty")
        for b in buckets:
            if b <= 0:
                raise InvalidBoundariesError("Histogram bucket boundaries must be positive")
        seen = set()
        for b in buckets:
            if b in seen:
                raise InvalidBoundariesError("Histogram bucket boundaries must be unique")
            seen.add(b)

    @property
    def name(self) -> str:
        return self._name

    @property
    def help(self) -> str:
        return self._help

    @property
    def labels(self) -> FrozenLabels:
        return self._labels

    @property
    def buckets(self) -> list[float]:
        return list(self._buckets)

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    @property
    def sum(self) -> float:
        with self._lock:
            return self._sum

    @property
    def bucket_counts(self) -> list[int]:
        with self._lock:
            return list(self._bucket_counts)

    def cumulative_counts(self) -> list[int]:
        with self._lock:
            cumulative: list[int] = []
            running = 0
            for i in range(len(self._buckets)):
                running += self._bucket_counts[i]
                cumulative.append(running)
            running += self._bucket_counts[-1]
            cumulative.append(running)
            return cumulative

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._count += 1
            idx = bisect_left(self._buckets, value)
            self._bucket_counts[idx] += 1

    def inc(self, delta: float = 1.0) -> None:
        raise InvalidOperationError("Histogram does not support inc operation")

    def dec(self, delta: float = 1.0) -> None:
        raise InvalidOperationError("Histogram does not support dec operation")

    def set(self, value: float) -> None:
        raise InvalidOperationError("Histogram does not support set operation")

    def quantile(self, q: float) -> float:
        if q < 0 or q > 1:
            raise InvalidOperationError("Quantile must be in range [0, 1]")
        with self._lock:
            if q == 0:
                return float(self._buckets[0]) if self._buckets else 0.0
            if q == 1:
                return float(self._buckets[-1]) if self._buckets else 0.0
            if self._count == 0:
                return 0.0
            target_rank = q * self._count
            cumulative = 0.0
            num_buckets = len(self._bucket_counts)
            for i in range(num_buckets):
                cumulative += self._bucket_counts[i]
                if cumulative >= target_rank:
                    if i < len(self._buckets):
                        lower = self._buckets[i - 1] if i > 0 else 0.0
                        upper = self._buckets[i]
                    else:
                        lower = self._buckets[-1]
                        upper = self._buckets[-1]
                    prev_cumulative = cumulative - self._bucket_counts[i]
                    offset = target_rank - prev_cumulative
                    if self._bucket_counts[i] > 0 and lower != upper:
                        return lower + (upper - lower) * (offset / self._bucket_counts[i])
                    return upper
            return float(self._buckets[-1]) if self._buckets else 0.0
