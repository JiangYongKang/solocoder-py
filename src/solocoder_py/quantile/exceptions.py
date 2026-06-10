from __future__ import annotations


class QuantileError(Exception):
    pass


class EmptyDigestError(QuantileError):
    pass


class InvalidQuantileError(QuantileError):
    pass


class InvalidValueError(QuantileError):
    pass


class InvalidWindowError(QuantileError):
    pass
