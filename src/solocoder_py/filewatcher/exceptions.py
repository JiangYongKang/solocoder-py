from __future__ import annotations


class FileWatcherError(Exception):
    pass


class FileWatcherNotRunningError(FileWatcherError):
    pass


class FileWatcherAlreadyRunningError(FileWatcherError):
    pass


class InvalidGlobPatternError(FileWatcherError):
    pass


class InvalidPathError(FileWatcherError):
    pass


class EventSourceError(FileWatcherError):
    pass
