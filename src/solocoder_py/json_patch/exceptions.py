from __future__ import annotations


class JsonPatchError(Exception):
    pass


class JsonPointerError(JsonPatchError):
    pass


class InvalidPointerError(JsonPointerError):
    pass


class PathNotFoundError(JsonPointerError):
    pass


class PatchOperationError(JsonPatchError):
    pass


class PatchTestFailedError(PatchOperationError):
    pass


class UnknownOperationError(PatchOperationError):
    pass


class AddOutOfBoundsError(PatchOperationError):
    pass
