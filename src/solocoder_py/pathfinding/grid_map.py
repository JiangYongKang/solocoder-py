from __future__ import annotations

from typing import List, Optional

from .exceptions import InvalidGridError, PointBlockedError, PointOutOfBoundsError
from .models import Point


class GridMap:
    def __init__(
        self,
        width: int,
        height: int,
        default_passable: bool = True,
        default_cost: float = 1.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise InvalidGridError("Grid width and height must be positive")
        if default_cost <= 0:
            raise InvalidGridError("Default cost must be positive")

        self._width = width
        self._height = height
        self._default_cost = default_cost
        self._passable: List[List[bool]] = [
            [default_passable for _ in range(width)] for _ in range(height)
        ]
        self._costs: List[List[float]] = [
            [default_cost for _ in range(width)] for _ in range(height)
        ]

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @classmethod
    def from_grid(
        cls,
        grid: List[List[bool]],
        cost_grid: Optional[List[List[float]]] = None,
    ) -> "GridMap":
        if not grid or not grid[0]:
            raise InvalidGridError("Grid cannot be empty")

        height = len(grid)
        width = len(grid[0])

        for row in grid:
            if len(row) != width:
                raise InvalidGridError("All rows must have the same width")

        grid_map = cls(width, height)

        for y in range(height):
            for x in range(width):
                grid_map._passable[y][x] = grid[y][x]

        if cost_grid is not None:
            if len(cost_grid) != height:
                raise InvalidGridError("Cost grid height does not match grid height")
            for row in cost_grid:
                if len(row) != width:
                    raise InvalidGridError("Cost grid width does not match grid width")
            for y in range(height):
                for x in range(width):
                    cost = cost_grid[y][x]
                    if cost <= 0:
                        raise InvalidGridError(f"Cost at ({x}, {y}) must be positive")
                    grid_map._costs[y][x] = cost

        return grid_map

    def is_in_bounds(self, point: Point) -> bool:
        return 0 <= point.x < self._width and 0 <= point.y < self._height

    def is_passable(self, point: Point) -> bool:
        if not self.is_in_bounds(point):
            return False
        return self._passable[point.y][point.x]

    def get_cost(self, point: Point) -> float:
        if not self.is_in_bounds(point):
            raise PointOutOfBoundsError(f"Point {point} is out of bounds")
        return self._costs[point.y][point.x]

    def set_passable(self, point: Point, passable: bool) -> None:
        if not self.is_in_bounds(point):
            raise PointOutOfBoundsError(f"Point {point} is out of bounds")
        self._passable[point.y][point.x] = passable

    def set_cost(self, point: Point, cost: float) -> None:
        if cost <= 0:
            raise InvalidGridError("Cost must be positive")
        if not self.is_in_bounds(point):
            raise PointOutOfBoundsError(f"Point {point} is out of bounds")
        self._costs[point.y][point.x] = cost

    def validate_point(self, point: Point, name: str = "Point") -> None:
        if not self.is_in_bounds(point):
            raise PointOutOfBoundsError(f"{name} {point} is out of bounds")
        if not self.is_passable(point):
            raise PointBlockedError(f"{name} {point} is blocked")

    def get_neighbors(
        self, point: Point, allow_diagonal: bool = True
    ) -> List[tuple[Point, float]]:
        directions = [
            (Point(1, 0), 1.0),
            (Point(-1, 0), 1.0),
            (Point(0, 1), 1.0),
            (Point(0, -1), 1.0),
        ]
        if allow_diagonal:
            sqrt2 = 2**0.5
            directions.extend([
                (Point(1, 1), sqrt2),
                (Point(1, -1), sqrt2),
                (Point(-1, 1), sqrt2),
                (Point(-1, -1), sqrt2),
            ])

        result = []
        for direction, base_cost in directions:
            neighbor = point + direction
            if self.is_passable(neighbor):
                cell_cost = self.get_cost(neighbor)
                result.append((neighbor, base_cost * cell_cost))

        return result
