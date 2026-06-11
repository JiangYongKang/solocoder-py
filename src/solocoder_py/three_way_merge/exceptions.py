from __future__ import annotations


class ThreeWayMergeError(Exception):
    pass


class InvalidInputError(ThreeWayMergeError):
    pass


class MergeTimeoutError(ThreeWayMergeError):
    pass
