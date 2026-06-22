from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


class SinglyLinkedListError(Exception):
    pass


@dataclass
class Node:
    value: Any
    next: Optional["Node"] = field(default=None)

    def __repr__(self) -> str:
        return f"Node(value={self.value!r})"
