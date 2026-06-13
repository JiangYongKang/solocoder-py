from __future__ import annotations


class HistogramError(Exception):
    pass


class InvalidBoundariesError(HistogramError):
    pass


class IncompatibleBoundariesError(HistogramError):
    pass


class InvalidQuantileError(HistogramError):
    pass


class EmptyHistogramError(HistogramError):
    pass
