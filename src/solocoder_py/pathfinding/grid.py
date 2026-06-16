from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .exceptions import CoordinateOutOfBoundsError, InvalidGridDimensionsError
from .models import Cell, CellType, Point


class GridMap:
    def __init__(
        self,
        width: int,
        height: int,
        default_weight: float = 1.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise InvalidGridDimensionsError(
                f"Grid dimensions must be positive, got width={width}, height={height}"
            )
        self._width = width
        self._height = height
        self._default_weight = default_weight
        self._cells: List[List[Cell]] = [
            [
                Cell(row=r, col=c, cell_type=CellType.PASSABLE, weight=default_weight)
                for c in range(width)
            ]
            for r in range(height)
        ]

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def in_bounds(self, point: Point) -> bool:
        return 0 <= point.x < self._width and 0 <= point.y < self._height

    def _validate_point(self, point: Point) -> None:
        if not self.in_bounds(point):
            raise CoordinateOutOfBoundsError(
                f"Point ({point.x}, {point.y}) is out of bounds for grid "
                f"({self._width}x{self._height})"
            )

    def get_cell(self, point: Point) -> Cell:
        self._validate_point(point)
        return self._cells[point.y][point.x]

    def is_passable(self, point: Point) -> bool:
        if not self.in_bounds(point):
            return False
        return self._cells[point.y][point.x].cell_type == CellType.PASSABLE

    def get_weight(self, point: Point) -> float:
        self._validate_point(point)
        return self._cells[point.y][point.x].weight

    def set_cell_type(self, point: Point, cell_type: CellType) -> None:
        self._validate_point(point)
        self._cells[point.y][point.x].cell_type = cell_type

    def set_weight(self, point: Point, weight: float) -> None:
        self._validate_point(point)
        if weight <= 0:
            raise ValueError(f"Weight must be positive, got {weight}")
        self._cells[point.y][point.x].weight = weight

    def set_passable(self, point: Point, passable: bool = True) -> None:
        self._validate_point(point)
        self._cells[point.y][point.x].cell_type = (
            CellType.PASSABLE if passable else CellType.IMPASSABLE
        )

    def set_wall(self, point: Point) -> None:
        self.set_passable(point, False)

    def set_block(self, point: Point) -> None:
        self.set_passable(point, False)

    def set_terrain(self, point: Point, weight: float, passable: bool = True) -> None:
        self._validate_point(point)
        if weight <= 0:
            raise ValueError(f"Weight must be positive, got {weight}")
        self._cells[point.y][point.x].weight = weight
        self._cells[point.y][point.x].cell_type = (
            CellType.PASSABLE if passable else CellType.IMPASSABLE
        )

    def get_neighbors(self, point: Point, allow_diagonal: bool = True) -> List[Tuple[Point, float]]:
        directions_cardinal = [
            (Point(0, -1), 1.0),
            (Point(0, 1), 1.0),
            (Point(-1, 0), 1.0),
            (Point(1, 0), 1.0),
        ]
        directions_diagonal = [
            (Point(-1, -1), 1.414),
            (Point(1, -1), 1.414),
            (Point(-1, 1), 1.414),
            (Point(1, 1), 1.414),
        ]
        directions = directions_cardinal[:]
        if allow_diagonal:
            directions.extend(directions_diagonal)

        neighbors: List[Tuple[Point, float]] = []
        for direction, base_cost in directions:
            neighbor = point + direction
            if not self.in_bounds(neighbor):
                continue
            if not self.is_passable(neighbor):
                continue
            if allow_diagonal and direction.x != 0 and direction.y != 0:
                corner_a = Point(point.x + direction.x, point.y)
                corner_b = Point(point.x, point.y + direction.y)
                if not self.is_passable(corner_a) or not self.is_passable(corner_b):
                    continue
            weight = self.get_weight(neighbor)
            neighbors.append((neighbor, base_cost * weight))
        return neighbors

    @classmethod
    def from_char_map(
        cls,
        char_map: List[str],
        weight_map: Optional[Dict[str, float]] = None,
    ) -> GridMap:
        if not char_map:
            raise InvalidGridDimensionsError("Char map cannot be empty")
        height = len(char_map)
        width = max(len(row) for row in char_map)
        if width == 0:
            raise InvalidGridDimensionsError("Char map rows cannot be empty")
        grid = cls(width=width, height=height)
        wall_chars = {"#", "X", "x"}
        if weight_map is None:
            weight_map = {}
        for r, row in enumerate(char_map):
            for c, ch in enumerate(row):
                pt = Point(x=c, y=r)
                if ch in wall_chars:
                    grid.set_wall(pt)
                elif ch in weight_map:
                    grid.set_terrain(pt, weight=weight_map[ch])
        return grid

    def __repr__(self) -> str:
        lines = []
        for r in range(self._height):
            row_str = ""
            for c in range(self._width):
                cell = self._cells[r][c]
                if cell.cell_type == CellType.IMPASSABLE:
                    row_str += "#"
                elif cell.weight != self._default_weight:
                    row_str += "~"
                else:
                    row_str += "."
            lines.append(row_str)
        return "\n".join(lines)
