from __future__ import annotations


class SlaTimerError(Exception):
    pass


class SlaTimerNotStartedError(SlaTimerError):
    pass


class SlaTimerAlreadyStartedError(SlaTimerError):
    pass


class SlaTimerNotRunningError(SlaTimerError):
    pass


class SlaTimerNotPausedError(SlaTimerError):
    pass


class SlaTimerExpiredError(SlaTimerError):
    pass


class InvalidSlaDurationError(SlaTimerError):
    pass


class InvalidWorkCalendarError(SlaTimerError):
    pass


class SlaTimerStateError(SlaTimerError):
    pass
