from __future__ import annotations

from enum import Enum
from typing import Optional


class ClockRelation(Enum):
    BEFORE = "before"
    AFTER = "after"
    CONCURRENT = "concurrent"
    EQUAL = "equal"


class VectorClock:
    def __init__(self, initial: Optional[dict[str, int]] = None) -> None:
        self._clocks: dict[str, int] = {}
        if initial:
            for node_id, count in initial.items():
                if count < 0:
                    raise ValueError(f"clock count must be non-negative, got {count} for node '{node_id}'")
                self._clocks[node_id] = count

    def tick(self, node_id: str) -> None:
        if not node_id:
            raise ValueError("node_id must not be empty")
        self._clocks[node_id] = self._clocks.get(node_id, 0) + 1

    def get(self, node_id: str) -> int:
        return self._clocks.get(node_id, 0)

    def nodes(self) -> set[str]:
        return set(self._clocks.keys())

    def to_dict(self) -> dict[str, int]:
        return dict(self._clocks)

    def copy(self) -> VectorClock:
        return VectorClock(self._clocks)

    def happens_before(self, other: VectorClock) -> bool:
        if not isinstance(other, VectorClock):
            raise TypeError("other must be a VectorClock")
        all_leq = True
        strictly_less = False
        all_nodes = self._clocks.keys() | other._clocks.keys()
        for node in all_nodes:
            a = self.get(node)
            b = other.get(node)
            if a > b:
                return False
            if a < b:
                strictly_less = True
        return all_leq and strictly_less

    def happens_after(self, other: VectorClock) -> bool:
        return other.happens_before(self)

    def is_concurrent_with(self, other: VectorClock) -> bool:
        if not isinstance(other, VectorClock):
            raise TypeError("other must be a VectorClock")
        return self != other and not self.happens_before(other) and not other.happens_before(self)

    def compare(self, other: VectorClock) -> ClockRelation:
        if self == other:
            return ClockRelation.EQUAL
        if self.happens_before(other):
            return ClockRelation.BEFORE
        if other.happens_before(self):
            return ClockRelation.AFTER
        return ClockRelation.CONCURRENT

    def merge(self, other: VectorClock) -> VectorClock:
        if not isinstance(other, VectorClock):
            raise TypeError("other must be a VectorClock")
        merged: dict[str, int] = {}
        all_nodes = self._clocks.keys() | other._clocks.keys()
        for node in all_nodes:
            merged[node] = max(self.get(node), other.get(node))
        return VectorClock(merged)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return NotImplemented
        all_nodes = self._clocks.keys() | other._clocks.keys()
        for node in all_nodes:
            if self.get(node) != other.get(node):
                return False
        return True

    def __hash__(self) -> int:
        return hash(frozenset(self._clocks.items()))

    def __repr__(self) -> str:
        return f"VectorClock({self._clocks!r})"
