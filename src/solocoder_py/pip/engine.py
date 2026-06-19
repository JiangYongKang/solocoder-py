from __future__ import annotations

import math
from enum import Enum
from typing import List

from .exceptions import InvalidPointError, InvalidPolygonError
from .models import Point, Polygon


class PointLocation(Enum):
    INSIDE = "inside"
    OUTSIDE = "outside"
    ON_BOUNDARY = "on_boundary"


_EPSILON = 1e-10


class RayCastingEngine:
    def __init__(self, epsilon: float = _EPSILON) -> None:
        self._epsilon = epsilon

    @property
    def epsilon(self) -> float:
        return self._epsilon

    def contains(self, polygon: Polygon, point: Point) -> PointLocation:
        self._validate_inputs(polygon, point)

        if self._is_on_boundary(polygon, point):
            return PointLocation.ON_BOUNDARY

        if self._ray_casting(polygon, point):
            return PointLocation.INSIDE
        return PointLocation.OUTSIDE

    def is_inside(self, polygon: Polygon, point: Point) -> bool:
        result = self.contains(polygon, point)
        return result == PointLocation.INSIDE or result == PointLocation.ON_BOUNDARY

    def is_outside(self, polygon: Polygon, point: Point) -> bool:
        return self.contains(polygon, point) == PointLocation.OUTSIDE

    def is_on_boundary(self, polygon: Polygon, point: Point) -> bool:
        self._validate_inputs(polygon, point)
        return self._is_on_boundary(polygon, point)

    def _validate_inputs(self, polygon: Polygon, point: Point) -> None:
        if not isinstance(polygon, Polygon):
            raise InvalidPolygonError(f"Expected Polygon, got {type(polygon)}")
        if not isinstance(point, Point):
            raise InvalidPointError(f"Expected Point, got {type(point)}")

    def _is_on_boundary(self, polygon: Polygon, point: Point) -> bool:
        n = polygon.vertex_count
        for i in range(n):
            v1 = polygon.vertices[i]
            v2 = polygon.vertices[(i + 1) % n]
            if self._point_on_segment(point, v1, v2):
                return True
        return False

    def _point_on_segment(self, p: Point, a: Point, b: Point) -> bool:
        cross = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x)
        if abs(cross) > self._epsilon:
            return False

        dot = (p.x - a.x) * (p.x - b.x) + (p.y - a.y) * (p.y - b.y)
        if dot > self._epsilon:
            return False

        return True

    def _ray_casting(self, polygon: Polygon, point: Point) -> bool:
        n = polygon.vertex_count
        px, py = point.x, point.y
        count = 0

        for i in range(n):
            v1 = polygon.vertices[i]
            v2 = polygon.vertices[(i + 1) % n]

            v1x, v1y = v1.x, v1.y
            v2x, v2y = v2.x, v2.y

            v1_above = v1y > py + self._epsilon
            v2_above = v2y > py + self._epsilon

            v1_on = abs(v1y - py) <= self._epsilon
            v2_on = abs(v2y - py) <= self._epsilon

            if v1_on and v2_on:
                continue

            if v1_above == v2_above and not v1_on and not v2_on:
                continue

            if v1_on:
                prev_idx = (i - 1 + n) % n
                prev_y = polygon.vertices[prev_idx].y
                prev_above = prev_y > py + self._epsilon
                if prev_above != v2_above:
                    if self._intersection_x_gt_px(v1x, v1y, v2x, v2y, px, py):
                        count += 1
                continue

            if v2_on:
                continue

            if v1_above != v2_above:
                if self._intersection_x_gt_px(v1x, v1y, v2x, v2y, px, py):
                    count += 1

        return count % 2 == 1

    def _intersection_x_gt_px(
        self,
        v1x: float,
        v1y: float,
        v2x: float,
        v2y: float,
        px: float,
        py: float,
    ) -> bool:
        t = (py - v1y) / (v2y - v1y)
        x_intersect = v1x + t * (v2x - v1x)
        return px < x_intersect - self._epsilon

    def contains_many(self, polygon: Polygon, points: List[Point]) -> List[PointLocation]:
        return [self.contains(polygon, p) for p in points]
