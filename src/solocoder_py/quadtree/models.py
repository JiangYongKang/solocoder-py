from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import InvalidRectangleError


@dataclass
class Point:
    x: float
    y: float
    data: Any = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))


@dataclass
class Rectangle:
    x: float
    y: float
    width: float
    height: float
    data: Any = None

    def __post_init__(self) -> None:
        if self.width < 0:
            raise InvalidRectangleError(f"width must be non-negative, got {self.width}")
        if self.height < 0:
            raise InvalidRectangleError(f"height must be non-negative, got {self.height}")

    @property
    def min_x(self) -> float:
        return self.x

    @property
    def min_y(self) -> float:
        return self.y

    @property
    def max_x(self) -> float:
        return self.x + self.width

    @property
    def max_y(self) -> float:
        return self.y + self.height

    def contains_point(self, point: Point) -> bool:
        return (
            self.min_x <= point.x <= self.max_x
            and self.min_y <= point.y <= self.max_y
        )

    def intersects(self, other: "Rectangle") -> bool:
        return (
            self.min_x <= other.max_x
            and self.max_x >= other.min_x
            and self.min_y <= other.max_y
            and self.max_y >= other.min_y
        )

    def contains(self, other: "Rectangle") -> bool:
        return (
            self.min_x <= other.min_x
            and self.max_x >= other.max_x
            and self.min_y <= other.min_y
            and self.max_y >= other.max_y
        )
