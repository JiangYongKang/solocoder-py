from __future__ import annotations


class HeavyHitterError(Exception):
    pass


class InvalidCapacityError(HeavyHitterError):
    pass


class InvalidKError(HeavyHitterError):
    pass


class InvalidEpsilonError(HeavyHitterError):
    pass


class InvalidDeltaError(HeavyHitterError):
    pass
