from __future__ import annotations


class MVCCError(Exception):
    pass


class TransactionError(MVCCError):
    pass


class TransactionStateError(TransactionError):
    pass


class WriteWriteConflictError(TransactionError):
    pass


class VersionNotFoundError(MVCCError):
    pass


class VersionReclaimedError(MVCCError):
    pass


class KeyNotFoundError(MVCCError):
    pass


class SnapshotInvalidError(MVCCError):
    pass
