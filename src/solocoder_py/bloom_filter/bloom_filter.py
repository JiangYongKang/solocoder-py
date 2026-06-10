from __future__ import annotations

import math
import threading
from abc import ABC, abstractmethod
from typing import Any, TypeVar


T = TypeVar("T", bound="_BloomFilterBase")


def calculate_optimal_m(expected_n: int, target_p: float) -> int:
    if expected_n <= 0:
        raise ValueError("expected_n must be a positive integer")
    if not (0 < target_p < 1):
        raise ValueError("target_p must be between 0 and 1 (exclusive)")
    m = -(expected_n * math.log(target_p)) / (math.log(2) ** 2)
    return max(1, math.ceil(m))


def calculate_optimal_k(expected_n: int, m: int) -> int:
    if expected_n <= 0:
        raise ValueError("expected_n must be a positive integer")
    if m <= 0:
        raise ValueError("m must be a positive integer")
    k = (m / expected_n) * math.log(2)
    return max(1, round(k))


def _serialize(element: Any) -> bytes:
    if isinstance(element, bytes):
        return element
    if isinstance(element, str):
        return element.encode("utf-8")
    if isinstance(element, (int, float, bool)):
        return repr(element).encode("utf-8")
    return repr(element).encode("utf-8")


def _fnv1a_64(data: bytes, offset: int) -> int:
    h = offset
    for byte in data:
        h ^= byte
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


class _BloomFilterBase(ABC):
    _FNV_OFFSET1 = 0xCBF29CE484222325
    _FNV_OFFSET2 = 0x9E3779B97F4A7C15

    def __init__(
        self,
        m: int | None = None,
        k: int | None = None,
        expected_n: int | None = None,
        target_p: float | None = None,
    ) -> None:
        if m is not None and k is not None:
            if m <= 0:
                raise ValueError("m must be a positive integer")
            if k <= 0:
                raise ValueError("k must be a positive integer")
            self._m = m
            self._k = k
        elif expected_n is not None and target_p is not None:
            self._m = calculate_optimal_m(expected_n, target_p)
            self._k = calculate_optimal_k(expected_n, self._m)
        else:
            raise ValueError(
                "Either (m, k) or (expected_n, target_p) must be provided"
            )

        self._count = 0
        self._lock = threading.RLock()
        self._init_storage()

    @abstractmethod
    def _init_storage(self) -> None:
        ...

    @property
    def m(self) -> int:
        return self._m

    @property
    def k(self) -> int:
        return self._k

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    def _hash_indices(self, element: Any) -> list[int]:
        data = _serialize(element)
        h1 = _fnv1a_64(data, self._FNV_OFFSET1)
        h2 = _fnv1a_64(data, self._FNV_OFFSET2)
        indices = []
        for i in range(self._k):
            idx = (h1 + i * h2) % self._m
            indices.append(idx)
        return indices

    @abstractmethod
    def add(self, element: Any) -> None:
        ...

    @abstractmethod
    def __contains__(self, element: Any) -> bool:
        ...

    def might_contain(self, element: Any) -> bool:
        return element in self

    def false_positive_rate(self) -> float:
        with self._lock:
            n = self._count
            m = self._m
            k = self._k
            if n == 0:
                return 0.0
            return (1 - math.exp(-k * n / m)) ** k

    @abstractmethod
    def is_compatible(self, other: "_BloomFilterBase") -> bool:
        ...

    @abstractmethod
    def union(self: T, other: T) -> T:
        ...

    def __or__(self: T, other: T) -> T:
        return self.union(other)

    @abstractmethod
    def intersection(self: T, other: T) -> T:
        ...

    def __and__(self: T, other: T) -> T:
        return self.intersection(other)

    def __len__(self) -> int:
        return self.count


class BloomFilter(_BloomFilterBase):
    def _init_storage(self) -> None:
        self._bits = bytearray((self._m + 7) // 8)

    def _get_bit(self, idx: int) -> bool:
        byte_idx = idx // 8
        bit_idx = idx % 8
        return bool(self._bits[byte_idx] & (1 << bit_idx))

    def _set_bit(self, idx: int) -> bool:
        byte_idx = idx // 8
        bit_idx = idx % 8
        mask = 1 << bit_idx
        was_set = bool(self._bits[byte_idx] & mask)
        self._bits[byte_idx] |= mask
        return was_set

    def add(self, element: Any) -> None:
        with self._lock:
            indices = self._hash_indices(element)
            all_already_set = True
            for idx in indices:
                was_set = self._set_bit(idx)
                if not was_set:
                    all_already_set = False
            if not all_already_set:
                self._count += 1

    def __contains__(self, element: Any) -> bool:
        with self._lock:
            indices = self._hash_indices(element)
            for idx in indices:
                if not self._get_bit(idx):
                    return False
            return True

    def is_compatible(self, other: "_BloomFilterBase") -> bool:
        return (
            isinstance(other, BloomFilter)
            and self._m == other._m
            and self._k == other._k
        )

    def union(self, other: "BloomFilter") -> "BloomFilter":
        if not self.is_compatible(other):
            raise ValueError(
                "Cannot compute union: filters must have the same m and k"
            )
        result = BloomFilter(m=self._m, k=self._k)
        with self._lock, other._lock:
            for i in range(len(self._bits)):
                result._bits[i] = self._bits[i] | other._bits[i]
            result._count = min(self._count + other._count, self._m)
        return result

    def intersection(self, other: "BloomFilter") -> "BloomFilter":
        if not self.is_compatible(other):
            raise ValueError(
                "Cannot compute intersection: filters must have the same m and k"
            )
        result = BloomFilter(m=self._m, k=self._k)
        with self._lock, other._lock:
            for i in range(len(self._bits)):
                result._bits[i] = self._bits[i] & other._bits[i]
            result._count = min(self._count, other._count)
        return result

    def __repr__(self) -> str:
        return (
            f"BloomFilter(m={self._m}, k={self._k}, count={self._count}, "
            f"fpr={self.false_positive_rate():.6f})"
        )


class CountingBloomFilter(_BloomFilterBase):
    MAX_COUNTER = 255

    def _init_storage(self) -> None:
        self._counters = bytearray(self._m)

    def add(self, element: Any) -> None:
        with self._lock:
            indices = self._hash_indices(element)
            for idx in indices:
                if self._counters[idx] < self.MAX_COUNTER:
                    self._counters[idx] += 1
            self._count += 1

    def remove(self, element: Any) -> None:
        with self._lock:
            indices = self._hash_indices(element)
            for idx in indices:
                if self._counters[idx] == 0:
                    raise ValueError(
                        "Cannot remove element that was not added: "
                        f"counter at index {idx} is already zero"
                    )
            for idx in indices:
                self._counters[idx] -= 1
            self._count -= 1

    def __contains__(self, element: Any) -> bool:
        with self._lock:
            indices = self._hash_indices(element)
            for idx in indices:
                if self._counters[idx] == 0:
                    return False
            return True

    def is_compatible(self, other: "_BloomFilterBase") -> bool:
        return (
            isinstance(other, CountingBloomFilter)
            and self._m == other._m
            and self._k == other._k
        )

    def union(self, other: "CountingBloomFilter") -> "CountingBloomFilter":
        if not self.is_compatible(other):
            raise ValueError(
                "Cannot compute union: filters must have the same m and k"
            )
        result = CountingBloomFilter(m=self._m, k=self._k)
        with self._lock, other._lock:
            for i in range(self._m):
                val = self._counters[i] + other._counters[i]
                result._counters[i] = min(val, self.MAX_COUNTER)
            result._count = min(self._count + other._count, self._m)
        return result

    def intersection(self, other: "CountingBloomFilter") -> "CountingBloomFilter":
        if not self.is_compatible(other):
            raise ValueError(
                "Cannot compute intersection: filters must have the same m and k"
            )
        result = CountingBloomFilter(m=self._m, k=self._k)
        with self._lock, other._lock:
            for i in range(self._m):
                result._counters[i] = min(self._counters[i], other._counters[i])
            result._count = min(self._count, other._count)
        return result

    def __repr__(self) -> str:
        return (
            f"CountingBloomFilter(m={self._m}, k={self._k}, count={self._count}, "
            f"fpr={self.false_positive_rate():.6f})"
        )
