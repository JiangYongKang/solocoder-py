from __future__ import annotations


class RWLockError(Exception):
    pass


class RWLockNotHeldError(RWLockError):
    pass


class RWLockNotAcquiredError(RWLockError):
    pass


class RWLockUpgradeError(RWLockError):
    pass
