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
        return self.priority < other.priority or self.priority == other.priority

    def __gt__(self, other: HeapEntry) -> bool:
        return not self.__le__(other)

    def __ge__(self, other: HeapEntry) -> bool:
        return not self.__lt__(other)
