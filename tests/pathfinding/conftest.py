from typing import List, Tuple

from solocoder_py.pathfinding import GridMap, Point


def build_empty_grid(width: int = 10, height: int = 10) -> GridMap:
    return GridMap(width, height, default_passable=True)


def build_grid_with_obstacles() -> Tuple[GridMap, Point, Point]:
    width, height = 10, 10
    grid = GridMap(width, height, default_passable=True)

    for x in range(3, 7):
        grid.set_passable(Point(x, 4), False)
    for y in range(0, 5):
        grid.set_passable(Point(6, y), False)

    start = Point(0, 0)
    goal = Point(9, 9)
    return grid, start, goal


def build_simple_obstacle_grid() -> Tuple[GridMap, Point, Point]:
    width, height = 5, 5
    grid = GridMap(width, height, default_passable=True)

    grid.set_passable(Point(2, 1), False)
    grid.set_passable(Point(2, 2), False)
    grid.set_passable(Point(2, 3), False)

    start = Point(0, 2)
    goal = Point(4, 2)
    return grid, start, goal


def build_cost_grid() -> Tuple[GridMap, Point, Point]:
    width, height = 5, 5
    grid = GridMap(width, height, default_passable=True, default_cost=1.0)

    for x in range(5):
        grid.set_cost(Point(x, 2), 10.0)

    start = Point(0, 0)
    goal = Point(4, 4)
    return grid, start, goal


def build_single_row_grid() -> Tuple[GridMap, Point, Point]:
    grid = GridMap(10, 1, default_passable=True)
    start = Point(0, 0)
    goal = Point(9, 0)
    return grid, start, goal


def build_single_column_grid() -> Tuple[GridMap, Point, Point]:
    grid = GridMap(1, 10, default_passable=True)
    start = Point(0, 0)
    goal = Point(0, 9)
    return grid, start, goal


def build_walled_corridor() -> Tuple[GridMap, Point, Point]:
    width, height = 7, 7
    grid = GridMap(width, height, default_passable=True)

    for x in range(7):
        grid.set_passable(Point(x, 0), False)
        grid.set_passable(Point(x, 6), False)
    for y in range(7):
        grid.set_passable(Point(0, y), False)
        grid.set_passable(Point(6, y), False)

    for x in range(1, 6):
        grid.set_passable(Point(x, 2), False)
        grid.set_passable(Point(x, 4), False)
    grid.set_passable(Point(3, 2), True)
    grid.set_passable(Point(3, 4), True)

    start = Point(1, 1)
    goal = Point(5, 5)
    return grid, start, goal


def build_disconnected_grid() -> Tuple[GridMap, Point, Point]:
    width, height = 6, 6
    grid = GridMap(width, height, default_passable=True)

    for x in range(6):
        grid.set_passable(Point(x, 3), False)

    start = Point(0, 0)
    goal = Point(5, 5)
    return grid, start, goal


def build_diagonal_obstacle_grid() -> Tuple[GridMap, Point, Point]:
    width, height = 6, 6
    grid = GridMap(width, height, default_passable=True)

    grid.set_passable(Point(2, 3), False)
    grid.set_passable(Point(3, 2), False)
    grid.set_passable(Point(3, 3), False)

    start = Point(0, 0)
    goal = Point(5, 5)
    return grid, start, goal
