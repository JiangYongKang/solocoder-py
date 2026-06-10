from __future__ import annotations


class WorkCalendarError(Exception):
    pass


class InvalidDateError(WorkCalendarError):
    pass


class InvalidWorkHoursError(WorkCalendarError):
    pass


class InvalidDurationError(WorkCalendarError):
    pass


class NoWorkDayFoundError(WorkCalendarError):
    pass
