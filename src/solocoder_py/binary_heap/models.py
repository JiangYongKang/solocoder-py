from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar


class SupportsLessThan(Protocol):
    def __lt__(self, other: SupportsLessThan) -> bool: ...


TPriority = TypeVar("TPriority", bound=SupportsLessThan)


@dataclass(order=True)
class HeapEntry:
    priority: SupportsLessThan
    element: Any = field(compare=False)
