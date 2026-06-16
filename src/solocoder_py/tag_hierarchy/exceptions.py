from __future__ import annotations


class TagHierarchyError(Exception):
    pass


class TagNotFoundError(TagHierarchyError):
    pass


class TagAlreadyExistsError(TagHierarchyError):
    pass


class ObjectNotFoundError(TagHierarchyError):
    pass


class InvalidTagError(TagHierarchyError):
    pass


class CircularReferenceError(TagHierarchyError):
    pass
