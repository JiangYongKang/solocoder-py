from __future__ import annotations


class TimeoutManagerError(Exception):
    pass


class ContextTerminalStateError(TimeoutManagerError):
    pass


class ContextNotFoundError(TimeoutManagerError):
    pass


class InvalidDeadlineError(TimeoutManagerError):
    pass


class InvalidCallbackError(TimeoutManagerError):
    pass
