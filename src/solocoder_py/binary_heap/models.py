from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar


class SupportsLessThan(Protocol):
    def __lt__(self, other: SupportsLessThan) -> bool: ...


TPriority = TypeVar("TPriority", bound=SupportsLessThan)


@dataclass
class HeapEntry:
    priority: SupportsLessThan
    element: Any

    def __lt__(self, other: HeapEntry) -> bool:
        return self.priority < other.priority

    def __le__(self, other: HeapEntry) -> bool:
        return not (other.priority < self.priority)

    def __gt__(self, other: HeapEntry) -> bool:
        return other.priority < self.priority

    def __ge__(self, other: HeapEntry) -> bool:
        return not (self.priority < other.priority)
