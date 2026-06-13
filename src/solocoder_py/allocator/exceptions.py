from __future__ import annotations


class AllocatorError(Exception):
    pass


class AllocationFailedError(AllocatorError):
    pass


class InvalidHandleError(AllocatorError):
    pass


class DeallocationFailedError(AllocatorError):
    pass
