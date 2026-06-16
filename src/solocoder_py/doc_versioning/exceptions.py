from __future__ import annotations


class DocVersioningError(Exception):
    pass


class DocumentNotFoundError(DocVersioningError):
    pass


class VersionNotFoundError(DocVersioningError):
    pass


class InvalidVersionError(DocVersioningError):
    pass


class BaseVersionMismatchError(DocVersioningError):
    pass


class EmptyContentError(DocVersioningError):
    pass


class MergeConflictError(DocVersioningError):
    pass
