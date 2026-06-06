from __future__ import annotations


class LockError(Exception):
    pass


class LockNotAcquiredError(LockError):
    pass


class LockNotHeldError(LockError):
    pass


class InvalidFenceTokenError(LockError):
    pass


class LockExpiredError(LockError):
    pass


class LockAcquisitionTimeoutError(LockError):
    pass
