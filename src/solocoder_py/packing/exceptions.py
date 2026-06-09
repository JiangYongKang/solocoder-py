from __future__ import annotations


class PackingError(Exception):
    pass


class InsufficientCapacityError(PackingError):
    pass


class InvalidItemError(PackingError):
    pass


class InvalidBinError(PackingError):
    pass
