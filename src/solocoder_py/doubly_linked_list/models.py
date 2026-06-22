from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


class DoublyLinkedListError(Exception):
    pass


class NodeNotFoundError(DoublyLinkedListError):
    pass


@dataclass
class Node:
    data: Any
    prev: Optional["Node"] = field(default=None, repr=False)
    next: Optional["Node"] = field(default=None, repr=False)
