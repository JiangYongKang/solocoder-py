from __future__ import annotations


class PathfindingError(Exception):
    pass


class CoordinateOutOfBoundsError(PathfindingError):
    pass


class StartNotPassableError(PathfindingError):
    pass


class GoalNotPassableError(PathfindingError):
    pass


class NoPathFoundError(PathfindingError):
    pass


class InvalidGridDimensionsError(PathfindingError):
    pass
