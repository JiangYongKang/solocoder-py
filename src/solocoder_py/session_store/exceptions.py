from __future__ import annotations


class SessionStoreError(Exception):
    pass


class SessionNotFoundError(SessionStoreError):
    pass


class SessionExpiredError(SessionStoreError):
    pass


class SessionIdleTimeoutError(SessionStoreError):
    pass


class SessionForciblyLoggedOutError(SessionStoreError):
    pass


class SessionLimitExceededError(SessionStoreError):
    pass


class InvalidSessionConfigError(SessionStoreError):
    pass


class InvalidUserIdError(SessionStoreError):
    pass


class InvalidSessionIdError(SessionStoreError):
    pass
