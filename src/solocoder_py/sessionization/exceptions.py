from __future__ import annotations


class SessionizationError(Exception):
    pass


class SessionError(SessionizationError):
    pass


class SessionNotFoundError(SessionError):
    pass


class InvalidEventError(SessionError):
    pass


class InvalidSubjectError(SessionError):
    pass


class InvalidThresholdError(SessionError):
    pass
