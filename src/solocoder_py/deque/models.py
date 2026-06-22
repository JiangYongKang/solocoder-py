from __future__ import annotations


class DequeError(Exception):
    pass


class DequeEmptyError(DequeError):
    pass


class DequeIndexError(DequeError, IndexError):
    pass
