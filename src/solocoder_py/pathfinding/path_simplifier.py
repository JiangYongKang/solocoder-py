from __future__ import annotations

from typing import List

from .models import PathResult, Point


def simplify_path(path: List[Point]) -> List[Point]:
    if len(path) <= 2:
        return list(path)

    simplified = [path[0]]
    for i in range(1, len(path) - 1):
        prev = simplified[-1]
        curr = path[i]
        nxt = path[i + 1]
        if not _are_collinear(prev, curr, nxt):
            simplified.append(curr)

    simplified.append(path[-1])
    return simplified


def _are_collinear(a: Point, b: Point, c: Point) -> bool:
    dx1 = b.x - a.x
    dy1 = b.y - a.y
    dx2 = c.x - b.x
    dy2 = c.y - b.y
    return dx1 * dy2 == dy1 * dx2


def simplify_path_result(result: PathResult) -> PathResult:
    if not result.found:
        return result
    simplified = simplify_path(result.path)
    return PathResult(
        path=result.path,
        cost=result.cost,
        simplified_path=simplified,
        failure_reason=result.failure_reason,
    )
