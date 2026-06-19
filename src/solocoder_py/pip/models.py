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

    @property
    def winding_order(self) -> float:
        n = len(self.vertices)
        area = 0.0
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            area += v1.x * v2.y - v2.x * v1.y
        return area

    def is_counterclockwise(self) -> bool:
        return self.winding_order > 0

    def is_clockwise(self) -> bool:
        return self.winding_order < 0

    def reverse(self) -> None:
        self.vertices.reverse()


@dataclass
class PolygonWithHoles:
    outer_ring: Polygon
    inner_rings: List[Polygon]
    validate_winding: bool = True

    def __post_init__(self) -> None:
        if self.outer_ring is None:
            raise InvalidPolygonError("Outer ring cannot be None")
        if not isinstance(self.outer_ring, Polygon):
            raise InvalidPolygonError(
                f"Outer ring must be a Polygon, got {type(self.outer_ring)}"
            )
        if self.inner_rings is None:
            raise InvalidPolygonError("Inner rings cannot be None")
        if not isinstance(self.inner_rings, list):
            raise InvalidPolygonError("Inner rings must be a list")
        for i, ring in enumerate(self.inner_rings):
            if not isinstance(ring, Polygon):
                raise InvalidPolygonError(
                    f"Inner ring {i} is not a Polygon instance: {type(ring)}"
                )

        if self.validate_winding:
            self._validate_winding_order()

    def _validate_winding_order(self) -> None:
        if not self.outer_ring.is_counterclockwise():
            raise InvalidPolygonError(
                "Outer ring must be counterclockwise (positive winding order)"
            )

        for i, ring in enumerate(self.inner_rings):
            if not ring.is_clockwise():
                raise InvalidPolygonError(
                    f"Inner ring {i} must be clockwise (negative winding order)"
                )

    def normalize(self) -> None:
        if not self.outer_ring.is_counterclockwise():
            self.outer_ring.reverse()
        for ring in self.inner_rings:
            if not ring.is_clockwise():
                ring.reverse()

    @classmethod
    def from_tuples(
        cls,
        outer_ring: List[Tuple[float, float]],
        inner_rings: List[List[Tuple[float, float]]],
    ) -> "PolygonWithHoles":
        outer = Polygon.from_tuples(outer_ring)
        inners = [Polygon.from_tuples(ring) for ring in inner_rings]
        instance = cls(
            outer_ring=outer, inner_rings=inners, validate_winding=False
        )
        instance.normalize()
        instance._validate_winding_order()
        return instance

    @property
    def hole_count(self) -> int:
        return len(self.inner_rings)
