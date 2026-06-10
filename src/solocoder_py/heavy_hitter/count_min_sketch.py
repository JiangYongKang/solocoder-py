from __future__ import annotations

import hashlib
import math
import threading
from typing import Any

from .exceptions import InvalidDeltaError, InvalidEpsilonError


class CountMinSketch:
    def __init__(
        self,
        epsilon: float = 0.001,
        delta: float = 0.99,
    ) -> None:
        if epsilon <= 0 or epsilon >= 1:
            raise InvalidEpsilonError("epsilon must be between 0 and 1, exclusive")
        if delta <= 0 or delta >= 1:
            raise InvalidDeltaError("delta must be between 0 and 1, exclusive")

        self._epsilon = epsilon
        self._delta = delta

        self._width: int = math.ceil(math.e / epsilon)
        self._depth: int = math.ceil(math.log(1 / delta))

        self._table: list[list[int]] = [
            [0] * self._width for _ in range(self._depth)
        ]
        self._lock = threading.RLock()
        self._total_count: int = 0
        self._hash_seeds: list[bytes] = [
            hashlib.sha256(f"seed_{i}".encode()).digest() for i in range(self._depth)
        ]

    @property
    def width(self) -> int:
        return self._width

    @property
    def depth(self) -> int:
        return self._depth

    @property
    def epsilon(self) -> float:
        return self._epsilon

    @property
    def delta(self) -> float:
        return self._delta

    @property
    def total_count(self) -> int:
        with self._lock:
            return self._total_count

    def add(self, item: Any, count: int = 1) -> None:
        if count <= 0:
            raise ValueError("count must be positive")

        item_bytes = self._to_bytes(item)

        with self._lock:
            for i in range(self._depth):
                index = self._hash(item_bytes, i)
                self._table[i][index] += count
            self._total_count += count

    def estimate(self, item: Any) -> int:
        item_bytes = self._to_bytes(item)

        with self._lock:
            min_count = self._table[0][self._hash(item_bytes, 0)]
            for i in range(1, self._depth):
                index = self._hash(item_bytes, i)
                current = self._table[i][index]
                if current < min_count:
                    min_count = current
            return min_count

    def lower_bound(self, item: Any) -> int:
        return self.estimate(item)

    def upper_bound(self, item: Any) -> int:
        return self.estimate(item) + int(self._epsilon * self._total_count)

    def error_bound(self) -> float:
        with self._lock:
            return self._epsilon * self._total_count

    def merge(self, other: "CountMinSketch") -> None:
        if other._epsilon != self._epsilon or other._delta != self._delta:
            raise ValueError(
                "Cannot merge sketches with different epsilon/delta parameters"
            )
        if other._width != self._width or other._depth != self._depth:
            raise ValueError(
                "Cannot merge sketches with different dimensions"
            )

        with self._lock:
            with other._lock:
                for i in range(self._depth):
                    for j in range(self._width):
                        self._table[i][j] += other._table[i][j]
                self._total_count += other._total_count

    def clear(self) -> None:
        with self._lock:
            for i in range(self._depth):
                for j in range(self._width):
                    self._table[i][j] = 0
            self._total_count = 0

    def _hash(self, item_bytes: bytes, row: int) -> int:
        hasher = hashlib.sha256()
        hasher.update(self._hash_seeds[row])
        hasher.update(item_bytes)
        hash_value = int.from_bytes(hasher.digest()[:8], byteorder="big")
        return hash_value % self._width

    def _to_bytes(self, item: Any) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        if isinstance(item, (int, float, bool)):
            return str(item).encode("utf-8")
        return repr(item).encode("utf-8")
