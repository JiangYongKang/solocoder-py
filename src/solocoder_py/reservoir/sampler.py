from __future__ import annotations

import heapq
import math
import random
from typing import Any, Iterable, Iterator, Optional

from .exceptions import (
    InvalidCapacityError,
    InvalidWeightError,
    SamplerClosedError,
)
from .models import SamplerState, WeightedItem


class ReservoirSampler:
    def __init__(self, capacity: int, seed: Optional[int] = None) -> None:
        if not isinstance(capacity, int):
            raise InvalidCapacityError("capacity must be an integer")
        if capacity < 0:
            raise InvalidCapacityError("capacity must be non-negative")
        self._capacity = capacity
        self._reservoir: list[Any] = []
        self._total_processed = 0
        self._closed = False
        self._rng = random.Random(seed)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def total_processed(self) -> int:
        return self._total_processed

    @property
    def sample_count(self) -> int:
        return len(self._reservoir)

    @property
    def closed(self) -> bool:
        return self._closed

    def feed(self, item: Any) -> None:
        if self._closed:
            raise SamplerClosedError("cannot feed data to a closed sampler")
        self._total_processed += 1
        i = self._total_processed
        if i <= self._capacity:
            self._reservoir.append(item)
        else:
            j = self._rng.randint(1, i)
            if j <= self._capacity:
                self._reservoir[j - 1] = item

    def feed_many(self, items: Iterable[Any]) -> None:
        for item in items:
            self.feed(item)

    def samples(self) -> list[Any]:
        return list(self._reservoir)

    def close(self) -> list[Any]:
        self._closed = True
        return self.samples()

    def get_state(self) -> SamplerState:
        return SamplerState(
            capacity=self._capacity,
            total_processed=self._total_processed,
            closed=self._closed,
            reservoir=list(self._reservoir),
        )

    def __len__(self) -> int:
        return len(self._reservoir)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._reservoir)

    def __contains__(self, item: Any) -> bool:
        return item in self._reservoir


class WeightedReservoirSampler:
    def __init__(self, capacity: int, seed: Optional[int] = None) -> None:
        if not isinstance(capacity, int):
            raise InvalidCapacityError("capacity must be an integer")
        if capacity < 0:
            raise InvalidCapacityError("capacity must be non-negative")
        self._capacity = capacity
        self._heap: list[WeightedItem] = []
        self._total_processed = 0
        self._closed = False
        self._rng = random.Random(seed)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def total_processed(self) -> int:
        return self._total_processed

    @property
    def sample_count(self) -> int:
        return len(self._heap)

    @property
    def closed(self) -> bool:
        return self._closed

    def feed(self, item: Any, weight: float) -> None:
        if self._closed:
            raise SamplerClosedError("cannot feed data to a closed sampler")
        if not isinstance(weight, (int, float)):
            raise InvalidWeightError("weight must be a number")
        if weight <= 0:
            raise InvalidWeightError("weight must be positive")
        self._total_processed += 1
        u = self._rng.random()
        key = u ** (1.0 / float(weight))
        weighted_item = WeightedItem(value=item, weight=float(weight), key=key)
        if len(self._heap) < self._capacity:
            heapq.heappush(self._heap, weighted_item)
        else:
            if self._heap and key > self._heap[0].key:
                heapq.heapreplace(self._heap, weighted_item)

    def feed_many(self, items: Iterable[tuple[Any, float]]) -> None:
        for item, weight in items:
            self.feed(item, weight)

    def samples(self) -> list[Any]:
        return [entry.value for entry in self._heap]

    def close(self) -> list[Any]:
        self._closed = True
        return self.samples()

    def get_state(self) -> SamplerState:
        return SamplerState(
            capacity=self._capacity,
            total_processed=self._total_processed,
            closed=self._closed,
            reservoir=self.samples(),
        )

    def __len__(self) -> int:
        return len(self._heap)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.samples())

    def __contains__(self, item: Any) -> bool:
        return any(entry.value == item for entry in self._heap)
