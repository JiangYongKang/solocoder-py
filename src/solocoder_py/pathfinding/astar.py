from __future__ import annotations

import heapq
from typing import Callable, Dict, List, Optional, Set, Tuple

from .exceptions import (
    CoordinateOutOfBoundsError,
    GoalNotPassableError,
    NoPathFoundError,
    StartNotPassableError,
)
from .grid import GridMap
from .models import PathResult, Point, SearchNode


def manhattan_distance(a: Point, b: Point) -> float:
    return float(abs(a.x - b.x) + abs(a.y - b.y))


def euclidean_distance(a: Point, b: Point) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def chebyshev_distance(a: Point, b: Point) -> float:
    return float(max(abs(a.x - b.x), abs(a.y - b.y)))


def octile_distance(a: Point, b: Point) -> float:
    dx = abs(a.x - b.x)
    dy = abs(a.y - b.y)
    return float(max(dx, dy) + (1.414 - 1) * min(dx, dy))


class AStarFinder:
    def __init__(
        self,
        grid: GridMap,
        allow_diagonal: bool = True,
        heuristic: Optional[Callable[[Point, Point], float]] = None,
    ) -> None:
        self._grid = grid
        self._allow_diagonal = allow_diagonal
        if heuristic is not None:
            self._heuristic = heuristic
        elif allow_diagonal:
            self._heuristic = octile_distance
        else:
            self._heuristic = manhattan_distance

    @property
    def grid(self) -> GridMap:
        return self._grid

    @property
    def allow_diagonal(self) -> bool:
        return self._allow_diagonal

    @property
    def heuristic(self) -> Callable[[Point, Point], float]:
        return self._heuristic

    def find_path(
        self,
        start: Point,
        goal: Point,
    ) -> PathResult:
        if not self._grid.in_bounds(start):
            raise CoordinateOutOfBoundsError(
                f"Start point ({start.x}, {start.y}) is out of bounds"
            )
        if not self._grid.in_bounds(goal):
            raise CoordinateOutOfBoundsError(
                f"Goal point ({goal.x}, {goal.y}) is out of bounds"
            )
        if not self._grid.is_passable(start):
            raise StartNotPassableError(
                f"Start point ({start.x}, {start.y}) is not passable"
            )
        if not self._grid.is_passable(goal):
            raise GoalNotPassableError(
                f"Goal point ({goal.x}, {goal.y}) is not passable"
            )

        if start == goal:
            return PathResult(path=[start], cost=0.0)

        open_set: List[Tuple[float, int, Point]] = []
        counter = 0
        start_g = 0.0
        start_h = self._heuristic(start, goal)
        counter += 1
        heapq.heappush(open_set, (start_g + start_h, counter, start))

        came_from: Dict[Point, Point] = {}
        g_score: Dict[Point, float] = {start: start_g}
        closed_set: Set[Point] = set()

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current in closed_set:
                continue
            closed_set.add(current)

            if current == goal:
                path = self._reconstruct_path(came_from, current)
                cost = g_score[goal]
                return PathResult(path=path, cost=cost)

            for neighbor, move_cost in self._grid.get_neighbors(
                current, self._allow_diagonal
            ):
                if neighbor in closed_set:
                    continue

                tentative_g = g_score[current] + move_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self._heuristic(neighbor, goal)
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor))

        return PathResult(
            path=[],
            cost=float("inf"),
            failure_reason=self._diagnose_failure(start, goal),
        )

    def _reconstruct_path(
        self, came_from: Dict[Point, Point], current: Point
    ) -> List[Point]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _diagnose_failure(self, start: Point, goal: Point) -> str:
        visited_count = 0
        reachable: Set[Point] = set()
        stack = [start]
        while stack:
            pt = stack.pop()
            if pt in reachable:
                continue
            reachable.add(pt)
            visited_count += 1
            for neighbor, _ in self._grid.get_neighbors(pt, self._allow_diagonal):
                if neighbor not in reachable:
                    stack.append(neighbor)

        if goal not in reachable:
            return (
                f"No path exists from ({start.x}, {start.y}) to "
                f"({goal.x}, {goal.y}): goal is not reachable "
                f"(disconnected by walls)"
            )
        return (
            f"No path found from ({start.x}, {start.y}) to "
            f"({goal.x}, {goal.y})"
        )
