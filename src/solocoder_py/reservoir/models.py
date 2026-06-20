from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WeightedItem:
    value: Any
    weight: float
    key: float = 0.0

    def __lt__(self, other: "WeightedItem") -> bool:
        return self.key < other.key

    def __le__(self, other: "WeightedItem") -> bool:
        return self.key <= other.key

    def __gt__(self, other: "WeightedItem") -> bool:
        return self.key > other.key

    def __ge__(self, other: "WeightedItem") -> bool:
        return self.key >= other.key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WeightedItem):
            return NotImplemented
        return (
            self.value == other.value
            and self.weight == other.weight
            and self.key == other.key
        )


@dataclass
class SamplerState:
    capacity: int
    total_processed: int
    closed: bool = False
    reservoir: list[Any] = field(default_factory=list)
