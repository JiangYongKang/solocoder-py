from __future__ import annotations

import random
import string
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .hyperloglog import HyperLogLog


@dataclass
class MemoryDataSource:
    name: str
    _data: list[Any] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def add(self, item: Any) -> None:
        with self._lock:
            self._data.append(item)

    def add_many(self, items: Iterable[Any]) -> None:
        with self._lock:
            self._data.extend(items)

    def items(self) -> list[Any]:
        with self._lock:
            return list(self._data)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.items())

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def feed_to(self, hll: HyperLogLog) -> None:
        with self._lock:
            for item in self._data:
                hll.add(item)

    def exact_cardinality(self) -> int:
        with self._lock:
            return len(set(self._data))

    def sample(self, k: int) -> list[Any]:
        with self._lock:
            if len(self._data) <= k:
                return list(self._data)
            return random.sample(self._data, k)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def generate_random_strings(count: int, length: int = 16, seed: Optional[int] = None) -> list[str]:
    if seed is not None:
        random.seed(seed)
    chars = string.ascii_letters + string.digits
    return ["".join(random.choices(chars, k=length)) for _ in range(count)]


def generate_random_integers(count: int, low: int = 0, high: int = 1000000, seed: Optional[int] = None) -> list[int]:
    if seed is not None:
        random.seed(seed)
    return [random.randint(low, high) for _ in range(count)]


def create_data_source_with_duplicates(
    name: str,
    unique_count: int,
    duplicate_factor: int = 10,
    seed: Optional[int] = None,
) -> MemoryDataSource:
    if seed is not None:
        random.seed(seed)
    unique_items = generate_random_strings(unique_count, seed=seed)
    data: list[str] = []
    for item in unique_items:
        copies = random.randint(1, duplicate_factor)
        data.extend([item] * copies)
    random.shuffle(data)
    source = MemoryDataSource(name=name)
    source.add_many(data)
    return source


def create_overlapping_data_sources(
    name_a: str,
    name_b: str,
    unique_a: int,
    unique_b: int,
    overlap: int,
    seed: Optional[int] = None,
) -> tuple[MemoryDataSource, MemoryDataSource]:
    if seed is not None:
        random.seed(seed)
    if overlap > min(unique_a, unique_b):
        raise ValueError("overlap cannot exceed the smaller of unique_a and unique_b")
    all_items = generate_random_strings(unique_a + unique_b - overlap, seed=seed)
    shared_items = all_items[:overlap]
    only_a = all_items[overlap:overlap + (unique_a - overlap)]
    only_b = all_items[overlap + (unique_a - overlap):]
    source_a = MemoryDataSource(name=name_a)
    source_a.add_many(shared_items + only_a)
    source_b = MemoryDataSource(name=name_b)
    source_b.add_many(shared_items + only_b)
    return source_a, source_b
