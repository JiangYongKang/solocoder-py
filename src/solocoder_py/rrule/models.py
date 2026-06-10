from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Set

from .enums import Frequency
from .exceptions import (
    InvalidCountError,
    InvalidDateRangeError,
    InvalidFrequencyError,
    InvalidIntervalError,
)


@dataclass
class RRule:
    frequency: Frequency
    start_date: date
    interval: int = 1
    count: Optional[int] = None
    end_date: Optional[date] = None
    exdates: Set[date] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not isinstance(self.frequency, Frequency):
            raise InvalidFrequencyError(
                f"Invalid frequency: {self.frequency}. "
                f"Must be one of: {', '.join(f.value for f in Frequency)}"
            )

        if not isinstance(self.interval, int) or self.interval <= 0:
            raise InvalidIntervalError(
                f"Invalid interval: {self.interval}. Must be a positive integer."
            )

        if self.count is not None:
            if not isinstance(self.count, int) or self.count <= 0:
                raise InvalidCountError(
                    f"Invalid count: {self.count}. Must be a positive integer or None."
                )

        if self.end_date is not None and self.start_date > self.end_date:
            raise InvalidDateRangeError(
                f"start_date {self.start_date} cannot be after end_date {self.end_date}"
            )

        if self.end_date is None and self.count is None:
            raise InvalidDateRangeError(
                "Either count or end_date must be specified to prevent infinite expansion."
            )

        self.exdates = set(self.exdates)
