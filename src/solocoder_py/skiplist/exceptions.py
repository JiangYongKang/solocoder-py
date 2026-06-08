from __future__ import annotations


class SkipListError(Exception):
    pass


class EmptySkipListError(SkipListError):
    pass


class ScoreNotFoundError(SkipListError):
    pass


class InvalidRankError(SkipListError):
    pass


class InvalidRangeError(SkipListError):
    pass
