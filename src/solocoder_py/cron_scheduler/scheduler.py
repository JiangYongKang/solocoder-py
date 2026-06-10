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
        next_m = self._expression.month.next_value(dt.month + 1)
        min_hour = self._expression.hour.sorted_values()[0]
        min_minute = self._expression.minute.sorted_values()[0]
        if next_m is not None:
            return dt.replace(month=next_m, day=1, hour=min_hour, minute=min_minute)
        next_year_month = self._expression.month.sorted_values()[0]
        return dt.replace(
            year=dt.year + 1,
            month=next_year_month,
            day=1,
            hour=min_hour,
            minute=min_minute,
        )

    def _advance_day(self, dt: datetime) -> datetime:
        year, month = dt.year, dt.month
        days_in_month = calendar.monthrange(year, month)[1]
        dom_field = self._expression.day_of_month
        dow_field = self._expression.day_of_week
        dom_all = self._is_all_values(dom_field)
        dow_all = self._is_all_values(dow_field)
        min_hour = self._expression.hour.sorted_values()[0]
        min_minute = self._expression.minute.sorted_values()[0]

        if dow_all and not dom_all:
            next_dom = dom_field.next_value(dt.day + 1)
            if next_dom is not None and next_dom <= days_in_month:
                return dt.replace(day=next_dom, hour=min_hour, minute=min_minute)
            return self._advance_month(dt)

        if dom_all and not dow_all:
            cron_dow = self._python_weekday_to_cron_dow(dt.weekday())
            next_dow = dow_field.next_value(cron_dow + 1)
            if next_dow is None:
                next_dow = dow_field.sorted_values()[0]
            days_ahead = (next_dow - cron_dow) % 7
            if days_ahead == 0:
                days_ahead = 7
            new_day = dt.day + days_ahead
            if new_day <= days_in_month:
                return dt.replace(day=new_day, hour=min_hour, minute=min_minute)
            return self._advance_month(dt)

        next_dom = dom_field.next_value(dt.day + 1)
        dom_day = next_dom if (next_dom is not None and next_dom <= days_in_month) else None

        cron_dow = self._python_weekday_to_cron_dow(dt.weekday())
        next_dow_val = dow_field.next_value(cron_dow + 1)
        if next_dow_val is None:
            next_dow_val = dow_field.sorted_values()[0]
        days_ahead = (next_dow_val - cron_dow) % 7
        if days_ahead == 0:
            days_ahead = 7
        dow_day = dt.day + days_ahead
        if dow_day > days_in_month:
            dow_day = None

        if dom_day is not None and dow_day is not None:
            best_day = min(dom_day, dow_day)
        elif dom_day is not None:
            best_day = dom_day
        elif dow_day is not None:
            best_day = dow_day
        else:
            return self._advance_month(dt)

        return dt.replace(day=best_day, hour=min_hour, minute=min_minute)

    def _advance_hour(self, dt: datetime) -> datetime:
        next_h = self._expression.hour.next_value(dt.hour + 1)
        min_minute = self._expression.minute.sorted_values()[0]
        if next_h is not None:
            return dt.replace(hour=next_h, minute=min_minute)
        return self._advance_day(dt)

    def _advance_minute(self, dt: datetime) -> datetime:
        next_min = self._expression.minute.next_value(dt.minute + 1)
        if next_min is not None:
            return dt.replace(minute=next_min)
        return self._advance_hour(dt)
