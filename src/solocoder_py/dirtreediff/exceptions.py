from __future__ import annotations


class DirTreeDiffError(Exception):
    pass


class InvalidSnapshotError(DirTreeDiffError):
    pass


class DuplicatePathError(InvalidSnapshotError):
    pass


class MissingRequiredFieldError(InvalidSnapshotError):
    pass


class InvalidNodeTypeError(InvalidSnapshotError):
    pass


class HashAlgorithmMismatchError(DirTreeDiffError):
    pass


class CaseInsensitivePathConflictError(DirTreeDiffError):
    pass


class SymlinkNotSupportedError(DirTreeDiffError):
    pass
