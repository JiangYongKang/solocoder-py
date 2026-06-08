from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar


T = TypeVar("T")


@dataclass
class PNCounterState:
    positive: dict[str, int] = field(default_factory=dict)
    negative: dict[str, int] = field(default_factory=dict)

    def value(self) -> int:
        return sum(self.positive.values()) - sum(self.negative.values())


@dataclass
class PNCounterDiff:
    added_positive: dict[str, int] = field(default_factory=dict)
    added_negative: dict[str, int] = field(default_factory=dict)
    increased_positive: dict[str, tuple[int, int]] = field(default_factory=dict)
    increased_negative: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class ORSetElement:
    tags: set[str] = field(default_factory=set)
    tombstones: set[str] = field(default_factory=set)


@dataclass
class ORSetState:
    elements: dict[Any, ORSetElement] = field(default_factory=dict)

    def value(self) -> set[Any]:
        result = set()
        for elem, info in self.elements.items():
            alive = info.tags - info.tombstones
            if alive:
                result.add(elem)
        return result


@dataclass
class ORSetDiff:
    added: dict[Any, set[str]] = field(default_factory=dict)
    removed: dict[Any, set[str]] = field(default_factory=dict)
    updated: dict[Any, tuple[set[str], set[str]]] = field(default_factory=dict)
