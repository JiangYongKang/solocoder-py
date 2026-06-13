from __future__ import annotations


class CounterError(Exception):
    pass


class InvalidDimensionError(CounterError):
    pass


class DimensionPathError(InvalidDimensionError):
    pass


class DimensionStructureMismatchError(CounterError):
    pass


class MergeError(CounterError):
    pass


