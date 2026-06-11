from __future__ import annotations


class AntiEntropyError(Exception):
    pass


class ReplicaError(AntiEntropyError):
    pass


class SyncError(AntiEntropyError):
    pass


class ConflictResolutionError(AntiEntropyError):
    pass


class VersionError(AntiEntropyError):
    pass
