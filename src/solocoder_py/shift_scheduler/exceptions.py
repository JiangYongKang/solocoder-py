from __future__ import annotations


class ShiftSchedulerError(Exception):
    pass


class StaffNotFoundError(ShiftSchedulerError):
    pass


class ShiftNotFoundError(ShiftSchedulerError):
    pass


class SwapRequestNotFoundError(ShiftSchedulerError):
    pass


class SwapRequestAlreadyProcessedError(ShiftSchedulerError):
    pass


class SwapRequestNotAuthorizedError(ShiftSchedulerError):
    pass


class PastDateSwapError(ShiftSchedulerError):
    pass


class OverlappingAssignmentError(ShiftSchedulerError):
    pass


class InvalidDateRangeError(ShiftSchedulerError):
    pass


class EmptyStaffListError(ShiftSchedulerError):
    pass


class UncoveredGapError(ShiftSchedulerError):
    pass


class DuplicateAssignmentError(ShiftSchedulerError):
    pass
