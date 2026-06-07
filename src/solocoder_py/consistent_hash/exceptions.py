from __future__ import annotations


class ConsistentHashError(Exception):
    pass


class EmptyRingError(ConsistentHashError):
    pass


class NodeNotFoundError(ConsistentHashError):
    pass


class NodeAlreadyExistsError(ConsistentHashError):
    pass


class InvalidVirtualNodesError(ConsistentHashError):
    pass


class InvalidWeightError(ConsistentHashError):
    pass
