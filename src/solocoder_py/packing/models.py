from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .exceptions import InvalidBinError, InvalidItemError


class PackingStrategyType(str, Enum):
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"


@dataclass
class Item:
    id: str
    size: int
    name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise InvalidItemError("Item size must be positive")

    @classmethod
    def create(cls, size: int, name: Optional[str] = None) -> "Item":
        return cls(
            id=str(uuid.uuid4()),
            size=size,
            name=name,
        )


@dataclass
class Bin:
    id: str
    capacity: int
    items: List[Item] = field(default_factory=list)
    name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise InvalidBinError("Bin capacity must be positive")

    @classmethod
    def create(cls, capacity: int, name: Optional[str] = None) -> "Bin":
        return cls(
            id=str(uuid.uuid4()),
            capacity=capacity,
            items=[],
            name=name,
        )

    @property
    def used_space(self) -> int:
        return sum(item.size for item in self.items)

    @property
    def remaining_space(self) -> int:
        return self.capacity - self.used_space

    @property
    def utilization(self) -> float:
        if self.capacity == 0:
            return 0.0
        return self.used_space / self.capacity

    def can_fit(self, item: Item) -> bool:
        return item.size <= self.remaining_space

    def add_item(self, item: Item) -> None:
        if not self.can_fit(item):
            raise InvalidItemError(
                f"Item size {item.size} exceeds remaining space {self.remaining_space} in bin {self.id}"
            )
        self.items.append(item)


@dataclass
class PackingResult:
    success: bool
    packed_bins: List[Bin]
    unpacked_items: List[Item]
    strategy_used: PackingStrategyType

    @property
    def total_capacity(self) -> int:
        return sum(b.capacity for b in self.packed_bins)

    @property
    def total_used_space(self) -> int:
        return sum(b.used_space for b in self.packed_bins)

    @property
    def total_remaining_space(self) -> int:
        return sum(b.remaining_space for b in self.packed_bins)

    @property
    def fragmentation_rate(self) -> float:
        if self.total_capacity == 0:
            return 0.0
        return self.total_remaining_space / self.total_capacity

    @property
    def overall_utilization(self) -> float:
        if self.total_capacity == 0:
            return 0.0
        return self.total_used_space / self.total_capacity

    def bin_utilizations(self) -> List[tuple[str, float]]:
        return [(b.id, b.utilization) for b in self.packed_bins]
