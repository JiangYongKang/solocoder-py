from __future__ import annotations


class LogSegmentError(Exception):
    pass


class OffsetNotFoundError(LogSegmentError):
    pass


class SegmentRecycledError(LogSegmentError):
    pass


class CompactionInProgressError(LogSegmentError):
    pass


class SegmentAlreadyRecycledError(LogSegmentError):
    pass
