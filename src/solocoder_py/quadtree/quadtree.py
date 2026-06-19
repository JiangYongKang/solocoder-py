from __future__ import annotations

from typing import List, Optional, Tuple

from .exceptions import (
    DuplicatePointError,
    InvalidCapacityError,
    InvalidDepthError,
    OutOfBoundsError,
)
from .models import Point, Rectangle


class _QuadNode:
    def __init__(self, boundary: Rectangle, depth: int, max_capacity: int, max_depth: int) -> None:
        self.boundary = boundary
        self.depth = depth
        self.max_capacity = max_capacity
        self.max_depth = max_depth
        self.points: List[Point] = []
        self.rectangles: List[Rectangle] = []
        self.northwest: Optional[_QuadNode] = None
        self.northeast: Optional[_QuadNode] = None
        self.southwest: Optional[_QuadNode] = None
        self.southeast: Optional[_QuadNode] = None

    @property
    def is_divided(self) -> bool:
        return self.northwest is not None

    @property
    def mid_x(self) -> float:
        return (self.boundary.min_x + self.boundary.max_x) / 2.0

    @property
    def mid_y(self) -> float:
        return (self.boundary.min_y + self.boundary.max_y) / 2.0

    def _subdivide(self) -> None:
        min_x = self.boundary.min_x
        min_y = self.boundary.min_y
        max_x = self.boundary.max_x
        max_y = self.boundary.max_y
        mid_x = self.mid_x
        mid_y = self.mid_y
        new_depth = self.depth + 1

        half_w = (max_x - min_x) / 2.0
        half_h = (max_y - min_y) / 2.0

        self.northwest = _QuadNode(
            Rectangle(x=min_x, y=mid_y, width=half_w, height=half_h),
            new_depth,
            self.max_capacity,
            self.max_depth,
        )
        self.northeast = _QuadNode(
            Rectangle(x=mid_x, y=mid_y, width=half_w, height=half_h),
            new_depth,
            self.max_capacity,
            self.max_depth,
        )
        self.southwest = _QuadNode(
            Rectangle(x=min_x, y=min_y, width=half_w, height=half_h),
            new_depth,
            self.max_capacity,
            self.max_depth,
        )
        self.southeast = _QuadNode(
            Rectangle(x=mid_x, y=min_y, width=half_w, height=half_h),
            new_depth,
            self.max_capacity,
            self.max_depth,
        )

        old_points = self.points
        old_rectangles = self.rectangles
        self.points = []
        self.rectangles = []

        for point in old_points:
            self._insert_point_into_subtree(point)

        for rect in old_rectangles:
            self._insert_rect_into_subtree(rect)

    def _get_quadrant_for_point(self, point: Point) -> Optional[_QuadNode]:
        if not self.is_divided:
            return None

        mid_x = self.mid_x
        mid_y = self.mid_y

        if point.x < mid_x:
            if point.y >= mid_y:
                return self.northwest
            else:
                return self.southwest
        else:
            if point.y >= mid_y:
                return self.northeast
            else:
                return self.southeast

    def _insert_point_into_subtree(self, point: Point) -> None:
        quadrant = self._get_quadrant_for_point(point)
        if quadrant is not None:
            quadrant.insert_point(point)
        else:
            self.points.append(point)

    def _get_quadrant_for_rect(self, rect: Rectangle) -> Optional[_QuadNode]:
        if not self.is_divided:
            return None

        mid_x = self.mid_x
        mid_y = self.mid_y

        fully_left = rect.max_x <= mid_x
        fully_right = rect.min_x >= mid_x
        fully_bottom = rect.max_y <= mid_y
        fully_top = rect.min_y >= mid_y

        if fully_left and fully_top:
            return self.northwest
        elif fully_right and fully_top:
            return self.northeast
        elif fully_left and fully_bottom:
            return self.southwest
        elif fully_right and fully_bottom:
            return self.southeast
        else:
            return None

    def _insert_rect_into_subtree(self, rect: Rectangle) -> None:
        quadrant = self._get_quadrant_for_rect(rect)
        if quadrant is not None:
            quadrant.insert_rectangle(rect)
        else:
            self.rectangles.append(rect)

    def insert_point(self, point: Point) -> None:
        if not self.boundary.contains_point(point):
            raise OutOfBoundsError(
                f"Point ({point.x}, {point.y}) is outside quadtree boundary"
            )

        if self.is_divided:
            self._insert_point_into_subtree(point)
            return

        for p in self.points:
            if p.x == point.x and p.y == point.y:
                raise DuplicatePointError(
                    f"Point at ({point.x}, {point.y}) already exists"
                )

        self.points.append(point)

        if len(self.points) + len(self.rectangles) > self.max_capacity:
            if self.depth < self.max_depth:
                self._subdivide()

    def insert_rectangle(self, rect: Rectangle) -> None:
        if not self.boundary.contains(rect):
            raise OutOfBoundsError(
                f"Rectangle at ({rect.x}, {rect.y}) with size {rect.width}x{rect.height} "
                f"is outside quadtree boundary"
            )

        if self.is_divided:
            quadrant = self._get_quadrant_for_rect(rect)
            if quadrant is not None:
                quadrant.insert_rectangle(rect)
                return

        self.rectangles.append(rect)

        if not self.is_divided and len(self.points) + len(self.rectangles) > self.max_capacity:
            if self.depth < self.max_depth:
                self._subdivide()

    def query(self, range_rect: Rectangle, results: List) -> None:
        if not self.boundary.intersects(range_rect):
            return

        for point in self.points:
            if range_rect.contains_point(point):
                results.append(point)

        for rect in self.rectangles:
            if range_rect.intersects(rect):
                results.append(rect)

        if self.is_divided:
            assert self.northwest is not None
            assert self.northeast is not None
            assert self.southwest is not None
            assert self.southeast is not None
            self.northwest.query(range_rect, results)
            self.northeast.query(range_rect, results)
            self.southwest.query(range_rect, results)
            self.southeast.query(range_rect, results)

    def get_all_objects(self) -> List:
        results: List = []
        results.extend(self.points)
        results.extend(self.rectangles)
        if self.is_divided:
            assert self.northwest is not None
            assert self.northeast is not None
            assert self.southwest is not None
            assert self.southeast is not None
            results.extend(self.northwest.get_all_objects())
            results.extend(self.northeast.get_all_objects())
            results.extend(self.southwest.get_all_objects())
            results.extend(self.southeast.get_all_objects())
        return results


class Quadtree:
    def __init__(
        self,
        boundary: Rectangle,
        max_capacity: int = 4,
        max_depth: int = 10,
    ) -> None:
        if max_capacity <= 0:
            raise InvalidCapacityError(
                f"max_capacity must be positive, got {max_capacity}"
            )
        if max_depth < 0:
            raise InvalidDepthError(
                f"max_depth must be non-negative, got {max_depth}"
            )

        self._boundary = Rectangle(
            x=boundary.x,
            y=boundary.y,
            width=boundary.width,
            height=boundary.height,
        )
        self._max_capacity = max_capacity
        self._max_depth = max_depth
        self._root = _QuadNode(self._boundary, 0, max_capacity, max_depth)
        self._point_count = 0
        self._rectangle_count = 0

    @property
    def boundary(self) -> Rectangle:
        return self._boundary

    @property
    def max_capacity(self) -> int:
        return self._max_capacity

    @property
    def max_depth(self) -> int:
        return self._max_depth

    @property
    def point_count(self) -> int:
        return self._point_count

    @property
    def rectangle_count(self) -> int:
        return self._rectangle_count

    @property
    def total_count(self) -> int:
        return self._point_count + self._rectangle_count

    def insert(self, obj) -> None:
        if isinstance(obj, Point):
            self.insert_point(obj)
        elif isinstance(obj, Rectangle):
            self.insert_rectangle(obj)
        else:
            raise TypeError(
                f"Unsupported object type: {type(obj).__name__}. "
                f"Expected Point or Rectangle."
            )

    def insert_point(self, point: Point) -> None:
        if not self._boundary.contains_point(point):
            raise OutOfBoundsError(
                f"Point ({point.x}, {point.y}) is outside quadtree boundary "
                f"({self._boundary.min_x}, {self._boundary.min_y}) to "
                f"({self._boundary.max_x}, {self._boundary.max_y})"
            )
        self._root.insert_point(point)
        self._point_count += 1

    def insert_rectangle(self, rect: Rectangle) -> None:
        if not self._boundary.contains(rect):
            raise OutOfBoundsError(
                f"Rectangle at ({rect.x}, {rect.y}) with size {rect.width}x{rect.height} "
                f"is outside quadtree boundary "
                f"({self._boundary.min_x}, {self._boundary.min_y}) to "
                f"({self._boundary.max_x}, {self._boundary.max_y})"
            )
        self._root.insert_rectangle(rect)
        self._rectangle_count += 1

    def query(self, range_rect: Rectangle) -> List:
        results: List = []
        self._root.query(range_rect, results)
        return results

    def get_all(self) -> List:
        return self._root.get_all_objects()

    def clear(self) -> None:
        self._root = _QuadNode(self._boundary, 0, self._max_capacity, self._max_depth)
        self._point_count = 0
        self._rectangle_count = 0
