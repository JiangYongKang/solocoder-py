from __future__ import annotations


class TagCacheError(Exception):
    pass


class TagNotFoundError(TagCacheError):
    pass


class EntryNotFoundError(TagCacheError):
    pass


class InvalidTagError(TagCacheError):
    pass


class AtomicOperationError(TagCacheError):
    pass
