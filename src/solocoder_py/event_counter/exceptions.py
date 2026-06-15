from __future__ import annotations


class EventCounterError(Exception):
    pass


class InvalidGranularityError(EventCounterError):
    pass


class InvalidTimeRangeError(EventCounterError):
    pass


class WindowExpiredError(EventCounterError):
    pass
