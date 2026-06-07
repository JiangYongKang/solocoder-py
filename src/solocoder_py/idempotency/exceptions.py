from __future__ import annotations


class IdempotencyError(Exception):
    pass


class IdempotencyKeyMismatchError(IdempotencyError):
    pass


class IdempotencyKeyConflictError(IdempotencyError):
    pass


class IdempotencyKeyExpiredError(IdempotencyError):
    pass


class IdempotencyProcessingError(IdempotencyError):
    pass
