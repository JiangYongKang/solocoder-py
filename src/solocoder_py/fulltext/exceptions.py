from __future__ import annotations


class FullTextError(Exception):
    pass


class DocumentNotFoundError(FullTextError):
    pass


class InvalidDocumentError(FullTextError):
    pass


class IndexError(FullTextError):
    pass
