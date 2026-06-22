from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar


class SupportsLessThan(Protocol):
    def __lt__(self, other: SupportsLessThan) -> bool: ...

    def __eq__(self, other: object) -> bool: ...


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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HeapEntry):
            return NotImplemented
        priority_equal = not (self.priority < other.priority) and not (other.priority < self.priority)
        return priority_equal and self.element == other.element
