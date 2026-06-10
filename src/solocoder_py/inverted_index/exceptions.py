from __future__ import annotations


class InvertedIndexError(Exception):
    pass


class EmptyQueryError(InvertedIndexError):
    pass


class DocumentExistsError(InvertedIndexError):
    pass


class InvalidCursorError(InvertedIndexError):
    pass
