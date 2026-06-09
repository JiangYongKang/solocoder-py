from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import Bin, Item


class PackingStrategy(ABC):
    @abstractmethod
    def find_bin(self, item: Item, bins: List[Bin]) -> Optional[Bin]:
        pass


class FirstFitStrategy(PackingStrategy):
    def find_bin(self, item: Item, bins: List[Bin]) -> Optional[Bin]:
        for b in bins:
            if b.can_fit(item):
                return b
        return None


class BestFitStrategy(PackingStrategy):
    def find_bin(self, item: Item, bins: List[Bin]) -> Optional[Bin]:
        best_bin: Optional[Bin] = None
        min_remaining: Optional[int] = None

        for b in bins:
            if b.can_fit(item):
                remaining = b.remaining_space - item.size
                if min_remaining is None or remaining < min_remaining:
                    min_remaining = remaining
                    best_bin = b

        return best_bin
