from __future__ import annotations


class SemverError(Exception):
    pass


class InvalidVersionError(SemverError):
    pass


class InvalidRangeError(SemverError):
    pass
