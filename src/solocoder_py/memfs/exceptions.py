from __future__ import annotations


class MemFSError(Exception):
    pass


class PathNotFoundError(MemFSError):
    pass


class FileNotFoundError(PathNotFoundError):
    pass


class DirectoryNotFoundError(PathNotFoundError):
    pass


class PermissionError(MemFSError):
    pass


class FileExistsError(MemFSError):
    pass


class DirectoryExistsError(MemFSError):
    pass


class IsADirectoryError(MemFSError):
    pass


class NotADirectoryError(MemFSError):
    pass


class DirectoryNotEmptyError(MemFSError):
    pass


class SymlinkLoopError(MemFSError):
    pass


class InvalidPathError(MemFSError):
    pass


class OperationNotPermittedError(MemFSError):
    pass
