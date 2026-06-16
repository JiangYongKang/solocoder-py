from __future__ import annotations


class DijkstraError(Exception):
    pass


class NodeNotFoundError(DijkstraError):
    pass


class NegativeWeightError(DijkstraError):
    pass


class UnreachableNodeError(DijkstraError):
    pass
