from __future__ import annotations

import random
from abc import ABC, abstractmethod
from bisect import bisect_left
from itertools import accumulate
from typing import List, Optional

from .models import Instance


class SelectionStrategy(ABC):
    @abstractmethod
    def select(self, instances: List[Instance]) -> Optional[Instance]:
        ...


class RoundRobinStrategy(SelectionStrategy):
    def __init__(self) -> None:
        self._counter: int = 0

    def select(self, instances: List[Instance]) -> Optional[Instance]:
        if not instances:
            return None
        idx = self._counter % len(instances)
        self._counter += 1
        return instances[idx]

    def reset(self) -> None:
        self._counter = 0


class WeightedRandomStrategy(SelectionStrategy):
    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()

    def select(self, instances: List[Instance]) -> Optional[Instance]:
        if not instances:
            return None
        candidates = [inst for inst in instances if inst.weight > 0]
        if not candidates:
            return None
        weights = [inst.weight for inst in candidates]
        total_weight = sum(weights)
        if total_weight <= 0:
            return None
        prefix = list(accumulate(weights))
        pick = self._rng.uniform(0, total_weight)
        idx = bisect_left(prefix, pick)
        if idx >= len(candidates):
            idx = len(candidates) - 1
        return candidates[idx]


class LeastConnectionsStrategy(SelectionStrategy):
    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()

    def select(self, instances: List[Instance]) -> Optional[Instance]:
        if not instances:
            return None
        min_conn = min(inst.active_connections for inst in instances)
        candidates = [
            inst for inst in instances if inst.active_connections == min_conn
        ]
        if len(candidates) == 1:
            return candidates[0]
        return self._rng.choice(candidates)
