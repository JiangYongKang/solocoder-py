from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class AllocationStrategy(Enum):
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"


@dataclass
class BlockInfo:
    start: int
    size: int
    allocated: bool


class Block:
    __slots__ = ("start", "size", "allocated", "free_node")

    def __init__(self, start: int, size: int, allocated: bool = False) -> None:
        self.start = start
        self.size = size
        self.allocated = allocated
        self.free_node: Any = None

    @property
    def end(self) -> int:
        return self.start + self.size

    def __repr__(self) -> str:
        status = "allocated" if self.allocated else "free"
        return f"Block(start={self.start}, size={self.size}, {status})"
