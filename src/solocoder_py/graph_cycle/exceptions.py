from __future__ import annotations


class GraphCycleError(Exception):
    pass


class NodeNotFoundError(GraphCycleError):
    pass
