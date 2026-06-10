from __future__ import annotations


class CronError(Exception):
    pass


class CronParseError(CronError):
    pass


class InvalidFieldValueError(CronParseError):
    def __init__(self, field: str, value: int, min_value: int, max_value: int) -> None:
        self.field = field
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(
            f"Invalid value {value} for field '{field}': must be between {min_value} and {max_value}"
        )


class InvalidRangeError(CronParseError):
    def __init__(self, field: str, start: int, end: int) -> None:
        self.field = field
        self.start = start
        self.end = end
        super().__init__(
            f"Invalid range for field '{field}': start ({start}) must be less than or equal to end ({end})"
        )


class InvalidStepError(CronParseError):
    def __init__(self, field: str, step: int, max_value: int) -> None:
        self.field = field
        self.step = step
        self.max_value = max_value
        super().__init__(
            f"Invalid step {step} for field '{field}': must be positive and not exceed {max_value}"
        )


class InvalidTimezoneError(CronError):
    def __init__(self, timezone_name: str) -> None:
        self.timezone_name = timezone_name
        super().__init__(f"Invalid timezone name: '{timezone_name}'")


class NoMatchingTimeError(CronError):
    def __init__(self, message: str = "No matching trigger time found within search limit") -> None:
        super().__init__(message)
