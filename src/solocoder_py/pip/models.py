from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from .exceptions import (
    EmptyPolygonError,
    InsufficientVerticesError,
    InvalidCoordinateError,
    InvalidPointError,
    InvalidPolygonError,
)


def _is_valid_coordinate(value: float) -> bool:
    if not isinstance(value, (int, float)):
        return False
    if isinstance(value, bool):
        return False
    return math.isfinite(value)


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not _is_valid_coordinate(self.x):
            raise InvalidCoordinateError(f"Invalid x coordinate: {self.x}")
        if not _is_valid_coordinate(self.y):
            raise InvalidCoordinateError(f"Invalid y coordinate: {self.y}")

    def __iter__(self):
        yield self.x
        yield self.y

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Polygon:
    vertices: List[Point]

    def __post_init__(self) -> None:
        if self.vertices is None:
            raise EmptyPolygonError("Polygon vertices cannot be None")
        if not isinstance(self.vertices, list):
            raise InvalidPolygonError("Polygon vertices must be a list")
        if len(self.vertices) == 0:
            raise EmptyPolygonError("Polygon cannot be empty")
        if len(self.vertices) < 3:
            raise InsufficientVerticesError(
                f"Polygon requires at least 3 vertices, got {len(self.vertices)}"
            )
        for i, v in enumerate(self.vertices):
            if not isinstance(v, Point):
                raise InvalidPolygonError(
                    f"Vertex {i} is not a Point instance: {type(v)}"
                )

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @classmethod
    def from_tuples(cls, vertices: List[Tuple[float, float]]) -> "Polygon":
        if vertices is None:
            raise EmptyPolygonError("Polygon vertices cannot be None")
        if not isinstance(vertices, list):
            raise InvalidPolygonError("Polygon vertices must be a list")
        point_list = []
        for v in vertices:
            if not isinstance(v, (tuple, list)) or len(v) != 2:
                raise InvalidPointError(
                    f"Vertex must be a 2-element tuple/list: {v}"
                )
            point_list.append(Point(x=v[0], y=v[1]))
        return cls(vertices=point_list)

    def get_edge(self, index: int) -> Tuple[Point, Point]:
        n = len(self.vertices)
        i = index % n
        j = (index + 1) % n
        return (self.vertices[i], self.vertices[j])
