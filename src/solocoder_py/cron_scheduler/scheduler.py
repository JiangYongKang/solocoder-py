from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .exceptions import InvalidTimezoneError, NoMatchingTimeError
from .models import CronExpression, CronField, FieldType
from .parser import CronParser

try:
    from typing import Union
    TZType = Union[ZoneInfo, timezone]
except ImportError:
    TZType = object


class CronScheduler:
    _MAX_SEARCH_YEARS = 4

    def __init__(
        self,
        expression: str | CronExpression,
        timezone_name: str = "UTC",
    ) -> None:
        if isinstance(expression, str):
            self._expression = CronParser.parse(expression)
        else:
            self._expression = expression

        self._cron_tz = self._resolve_timezone(timezone_name)
        self._timezone_name = timezone_name

    @property
    def expression(self) -> CronExpression:
        return self._expression

    @property
    def timezone_name(self) -> str:
        return self._timezone_name

    @staticmethod
    def _resolve_timezone(timezone_name: str) -> TZType:
        if timezone_name.upper() == "UTC":
            return timezone.utc
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            raise InvalidTimezoneError(timezone_name)

    def next_trigger(
        self,
        after: Optional[datetime] = None,
        target_timezone_name: Optional[str] = None,
    ) -> datetime:
        if after is None:
            after = datetime.now(timezone.utc)

        target_tz = self._cron_tz
        if target_timezone_name is not None:
            target_tz = self._resolve_timezone(target_timezone_name)

        if after.tzinfo is None:
            after_utc = after.replace(tzinfo=timezone.utc)
        else:
            after_utc = after.astimezone(timezone.utc)

        after_in_cron = after_utc.astimezone(self._cron_tz)
        candidate = self._start_from_next_minute(after_in_cron)

        result = self._find_next_trigger(candidate)
        if result is None:
            raise NoMatchingTimeError()

        result_utc = result.astimezone(timezone.utc)
        return result_utc.astimezone(target_tz).replace(second=0, microsecond=0)

    def next_n_triggers(
        self,
        n: int,
        after: Optional[datetime] = None,
        target_timezone_name: Optional[str] = None,
    ) -> list[datetime]:
        if n <= 0:
            raise ValueError("n must be positive")

        results: list[datetime] = []
        current = after
        for _ in range(n):
            current = self.next_trigger(
                after=current,
                target_timezone_name=target_timezone_name,
            )
            results.append(current)
        return results

    @staticmethod
    def _start_from_next_minute(dt: datetime) -> datetime:
        dt = dt.replace(second=0, microsecond=0)
        return dt + timedelta(minutes=1)

    def _find_next_trigger(self, start: datetime) -> Optional[datetime]:
        limit_year = start.year + self._MAX_SEARCH_YEARS

        candidate = start
        while candidate.year <= limit_year:
            if not self._matches_month(candidate):
                candidate = self._advance_month(candidate)
                continue

            if not self._matches_day(candidate):
                candidate = self._advance_day(candidate)
                continue

            if not self._matches_hour(candidate):
                candidate = self._advance_hour(candidate)
                continue

            if not self._matches_minute(candidate):
                candidate = self._advance_minute(candidate)
                continue

            return candidate

        return None

    def _matches_month(self, dt: datetime) -> bool:
        return self._expression.month.contains(dt.month)

    @staticmethod
    def _python_weekday_to_cron_dow(weekday: int) -> int:
        return (weekday + 1) % 7

    def _matches_day(self, dt: datetime) -> bool:
        dom_field = self._expression.day_of_month
        dow_field = self._expression.day_of_week
        dom_all = self._is_all_values(dom_field)
        dow_all = self._is_all_values(dow_field)
        cron_dow = self._python_weekday_to_cron_dow(dt.weekday())

        if dom_all and dow_all:
            return True
        if dom_all:
            return dow_field.contains(cron_dow)
        if dow_all:
            return dom_field.contains(dt.day)
        return dom_field.contains(dt.day) or dow_field.contains(cron_dow)

    def _matches_hour(self, dt: datetime) -> bool:
        return self._expression.hour.contains(dt.hour)

    def _matches_minute(self, dt: datetime) -> bool:
        return self._expression.minute.contains(dt.minute)

    @staticmethod
    def _is_all_values(field: CronField) -> bool:
        min_val, max_val = field.min_value, field.max_value
        return len(field) == (max_val - min_val + 1)

    def _advance_month(self, dt: datetime) -> datetime:
        if dt.month == 12:
            return dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0)
        return dt.replace(month=dt.month + 1, day=1, hour=0, minute=0)

    def _advance_day(self, dt: datetime) -> datetime:
        year, month = dt.year, dt.month
        days_in_month = calendar.monthrange(year, month)[1]

        if dt.day >= days_in_month:
            return self._advance_month(dt)

        return dt.replace(day=dt.day + 1, hour=0, minute=0)

    def _advance_hour(self, dt: datetime) -> datetime:
        if dt.hour >= 23:
            return self._advance_day(dt)
        return dt.replace(hour=dt.hour + 1, minute=0)

    def _advance_minute(self, dt: datetime) -> datetime:
        if dt.minute >= 59:
            return self._advance_hour(dt)
        return dt.replace(minute=dt.minute + 1)
