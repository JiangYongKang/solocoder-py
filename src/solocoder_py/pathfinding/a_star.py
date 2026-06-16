from __future__ import annotations

import heapq
from typing import Callable, Dict, List, Optional

from .exceptions import PathNotFoundError
from .grid_map import GridMap
from .models import PathResult, Point


def manhattan_heuristic(start: Point, goal: Point) -> float:
    dx = abs(start.x - goal.x)
    dy = abs(start.y - goal.y)
    return float(dx + dy)


def euclidean_heuristic(start: Point, goal: Point) -> float:
    dx = start.x - goal.x
    dy = start.y - goal.y
    return (dx * dx + dy * dy) ** 0.5


def chebyshev_heuristic(start: Point, goal: Point) -> float:
    dx = abs(start.x - goal.x)
    dy = abs(start.y - goal.y)
    return float(max(dx, dy))


def octile_heuristic(start: Point, goal: Point) -> float:
    dx = abs(start.x - goal.x)
    dy = abs(start.y - goal.y)
    return float(max(dx, dy) + (2**0.5 - 1) * min(dx, dy))


class AStarPathfinder:
    def __init__(
        self,
        grid_map: GridMap,
        heuristic: Optional[Callable[[Point, Point], float]] = None,
        allow_diagonal: bool = True,
        simplify_path: bool = True,
    ) -> None:
        self._grid_map = grid_map
        self._heuristic = heuristic if heuristic is not None else manhattan_heuristic
        self._allow_diagonal = allow_diagonal
        self._simplify_path = simplify_path

    @property
    def grid_map(self) -> GridMap:
        return self._grid_map

    def find_path(self, start: Point, goal: Point) -> PathResult:
        try:
            self._grid_map.validate_point(start, "Start point")
            self._grid_map.validate_point(goal, "Goal point")
        except Exception as e:
            return PathResult(success=False, error_message=str(e))

        if start == goal:
            return PathResult(path=[start], total_cost=0.0, success=True)

        open_set: List[tuple[float, int, Point]] = []
        counter = 0

        g_score: Dict[Point, float] = {start: 0.0}
        f_score: Dict[Point, float] = {start: self._heuristic(start, goal)}
        came_from: Dict[Point, Point] = {}

        heapq.heappush(open_set, (f_score[start], counter, start))
        counter += 1

        closed_set: set[Point] = set()

        while open_set:
            current_f, _, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            if current == goal:
                path = self._reconstruct_path(came_from, current)
                total_cost = g_score[current]
                if self._simplify_path:
                    path = self._simplify_collinear(path)
                return PathResult(path=path, total_cost=total_cost, success=True)

            closed_set.add(current)

            for neighbor, move_cost in self._grid_map.get_neighbors(
                current, self._allow_diagonal
            ):
                if neighbor in closed_set:
                    continue

                tentative_g = g_score[current] + move_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                    counter += 1

        return PathResult(
            success=False,
            error_message="No path found: start and goal are not connected",
        )

    def find_path_or_raise(self, start: Point, goal: Point) -> PathResult:
        result = self.find_path(start, goal)
        if not result.is_found:
            raise PathNotFoundError(result.error_message or "No path found")
        return result

    def _reconstruct_path(self, came_from: Dict[Point, Point], current: Point) -> List[Point]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _simplify_collinear(self, path: List[Point]) -> List[Point]:
        if len(path) <= 2:
            return path

        simplified = [path[0]]

        for i in range(1, len(path) - 1):
            prev = simplified[-1]
            curr = path[i]
            next_p = path[i + 1]

            if not self._are_collinear(prev, curr, next_p):
                simplified.append(curr)

        simplified.append(path[-1])
        return simplified

    @staticmethod
    def _are_collinear(p1: Point, p2: Point, p3: Point) -> bool:
        return (p2.x - p1.x) * (p3.y - p1.y) == (p2.y - p1.y) * (p3.x - p1.x)
