from __future__ import annotations


class CursorPaginationError(Exception):
    pass


class InvalidCursorError(CursorPaginationError):
    pass


class CursorTamperedError(InvalidCursorError):
    pass


class CursorExpiredError(InvalidCursorError):
    pass


class InvalidPageSizeError(CursorPaginationError):
    pass


class InvalidDirectionError(CursorPaginationError):
    pass


class InvalidSortFieldError(CursorPaginationError):
    pass
