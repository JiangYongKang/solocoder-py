from __future__ import annotations


class JSONPathError(Exception):
    pass


class InvalidPathError(JSONPathError):
    pass


class UnexpectedTokenError(JSONPathError):
    pass
