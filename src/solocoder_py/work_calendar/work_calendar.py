from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, time
from typing import Iterable, List, Optional, Set

from .exceptions import InvalidDurationError, NoWorkDayFoundError
from .models import CalendarConfig, WorkDaySchedule, WorkTimeRange


@dataclass
class WorkCalendar:
    config: CalendarConfig = field(default_factory=CalendarConfig)

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = CalendarConfig()

    def is_weekend(self, d: date) -> bool:
        return d.weekday() >= 5

    def is_holiday(self, d: date) -> bool:
        return d in self.config.holidays

    def is_extra_workday(self, d: date) -> bool:
        return d in self.config.workdays

    def is_workday(self, d: date) -> bool:
        if self.is_extra_workday(d):
            return True
        if self.is_holiday(d):
            return False
        return not self.is_weekend(d)

    def add_work_days(self, start_date: date, days: int) -> date:
        if days == 0:
            return start_date

        current = start_date
        direction = 1 if days > 0 else -1
        remaining = abs(days)
        max_iterations = 3650

        while remaining > 0 and max_iterations > 0:
            current += timedelta(days=direction)
            if self.is_workday(current):
                remaining -= 1
            max_iterations -= 1

        if remaining > 0:
            raise NoWorkDayFoundError("Cannot find enough workdays within the search range")

        return current

    def add_work_hours(self, start_dt: datetime, hours: float) -> datetime:
        if hours < 0:
            raise InvalidDurationError("Work hours cannot be negative")
        if hours == 0:
            return start_dt

        schedule = self.config.work_schedule
        current_dt = start_dt
        remaining_hours = hours

        while remaining_hours > 0:
            current_date = current_dt.date()

            if not self.is_workday(current_date):
                current_dt = self._next_workday_start(current_dt)
                continue

            work_periods = schedule.get_work_periods()
            found_period = False

            for period in work_periods:
                period_start_dt = datetime.combine(current_date, period.start)
                period_end_dt = datetime.combine(current_date, period.end)

                if current_dt < period_start_dt:
                    current_dt = period_start_dt

                if current_dt >= period_end_dt:
                    continue

                found_period = True
                available_hours = (period_end_dt - current_dt).total_seconds() / 3600.0

                if remaining_hours <= available_hours:
                    current_dt += timedelta(hours=remaining_hours)
                    remaining_hours = 0
                    break
                else:
                    remaining_hours -= available_hours
                    current_dt = period_end_dt

            if not found_period or remaining_hours > 0:
                current_dt = self._next_workday_start(current_dt)

        return current_dt

    def _next_workday_start(self, dt: datetime) -> datetime:
        schedule = self.config.work_schedule
        current_date = dt.date()

        if self.is_workday(current_date):
            work_start = schedule.morning.start
            if dt.time() < work_start:
                return datetime.combine(current_date, work_start)

        next_date = current_date + timedelta(days=1)
        max_iterations = 3650
        while not self.is_workday(next_date) and max_iterations > 0:
            next_date += timedelta(days=1)
            max_iterations -= 1

        if not self.is_workday(next_date):
            raise NoWorkDayFoundError("Cannot find any workday within the search range")

        return datetime.combine(next_date, schedule.morning.start)

    def natural_days_to_work_days(self, start_date: date, natural_days: int) -> int:
        if natural_days == 0:
            return 0

        work_days = 0
        direction = 1 if natural_days > 0 else -1
        remaining = abs(natural_days)
        current = start_date

        for _ in range(remaining):
            current += timedelta(days=direction)
            if self.is_workday(current):
                work_days += 1

        return work_days if natural_days > 0 else -work_days

    def work_days_to_natural_days(self, start_date: date, work_days: int) -> int:
        if work_days == 0:
            return 0

        target_date = self.add_work_days(start_date, work_days)
        delta = target_date - start_date
        return abs(delta.days) if work_days > 0 else -abs(delta.days)

    def count_work_days_in_range(self, start_date: date, end_date: date) -> int:
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        count = 0
        current = start_date
        while current <= end_date:
            if self.is_workday(current):
                count += 1
            current += timedelta(days=1)

        return count

    def get_workdays_between(self, start_date: date, end_date: date) -> List[date]:
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        result: List[date] = []
        current = start_date
        while current <= end_date:
            if self.is_workday(current):
                result.append(current)
            current += timedelta(days=1)

        return result

    def set_holidays(self, holidays: Iterable[date]) -> None:
        holiday_set = set(holidays)
        workday_set = set(self.config.workdays)
        conflicting = holiday_set & workday_set
        if conflicting:
            raise ValueError(f"Dates cannot be both holiday and workday: {conflicting}")
        self.config = CalendarConfig(
            holidays=frozenset(holiday_set),
            workdays=self.config.workdays,
            work_schedule=self.config.work_schedule,
        )

    def set_workdays(self, workdays: Iterable[date]) -> None:
        workday_set = set(workdays)
        holiday_set = set(self.config.holidays)
        conflicting = workday_set & holiday_set
        if conflicting:
            raise ValueError(f"Dates cannot be both holiday and workday: {conflicting}")
        self.config = CalendarConfig(
            holidays=self.config.holidays,
            workdays=frozenset(workday_set),
            work_schedule=self.config.work_schedule,
        )

    def set_work_schedule(self, schedule: WorkDaySchedule) -> None:
        self.config = CalendarConfig(
            holidays=self.config.holidays,
            workdays=self.config.workdays,
            work_schedule=schedule,
        )
