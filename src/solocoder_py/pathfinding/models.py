from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class CellType(Enum):
    PASSABLE = "passable"
    IMPASSABLE = "impassable"


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def __iter__(self):
        yield self.x
        yield self.y

    def __add__(self, other: Point) -> Point:
        return Point(x=self.x + other.x, y=self.y + other.y)


@dataclass
class Cell:
    row: int
    col: int
    cell_type: CellType = CellType.PASSABLE
    weight: float = 1.0


@dataclass
class PathResult:
    path: List[Point]
    cost: float
    simplified_path: Optional[List[Point]] = None
    failure_reason: Optional[str] = None

    @property
    def found(self) -> bool:
        return self.failure_reason is None and len(self.path) > 0

    @property
    def length(self) -> int:
        return len(self.path)


@dataclass
class SearchNode:
    point: Point
    g: float = float("inf")
    h: float = 0.0
    parent: Optional[SearchNode] = None

    @property
    def f(self) -> float:
        return self.g + self.h
