from __future__ import annotations

from datetime import date
from typing import List

from .enums import Frequency
from .models import RRule


class RRuleExpander:
    def expand(self, rule: RRule) -> List[date]:
        dates: List[date] = []
        current = rule.start_date
        generated_count = 0
        original_day = rule.start_date.day

        while True:
            if rule.count is not None and generated_count >= rule.count:
                break

            if rule.end_date is not None and current > rule.end_date:
                break

            if current not in rule.exdates:
                dates.append(current)
                generated_count += 1

            current = self._advance(current, rule.frequency, rule.interval, original_day)

        return dates

    def _advance(self, current: date, frequency: Frequency, interval: int, original_day: int) -> date:
        if frequency == Frequency.DAILY:
            return self._add_days(current, interval)
        elif frequency == Frequency.WEEKLY:
            return self._add_days(current, interval * 7)
        elif frequency == Frequency.MONTHLY:
            return self._add_months(current, interval, original_day)
        elif frequency == Frequency.YEARLY:
            return self._add_years(current, interval, original_day)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")

    def _add_days(self, current: date, days: int) -> date:
        try:
            return current.replace(day=current.day + days)
        except ValueError:
            month = current.month
            year = current.year
            remaining_days = days
            while remaining_days > 0:
                days_in_month = self._days_in_month(year, month)
                if current.day + remaining_days <= days_in_month:
                    return current.replace(
                        year=year, month=month, day=current.day + remaining_days
                    )
                remaining_days -= days_in_month - current.day + 1
                current = current.replace(day=1)
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                current = current.replace(year=year, month=month)
            return current

    def _add_months(self, current: date, months: int, original_day: int) -> date:
        total_months = current.year * 12 + current.month - 1 + months
        new_year = total_months // 12
        new_month = total_months % 12 + 1
        max_day = self._days_in_month(new_year, new_month)
        new_day = min(original_day, max_day)
        return date(new_year, new_month, new_day)

    def _add_years(self, current: date, years: int, original_day: int) -> date:
        new_year = current.year + years
        max_day = self._days_in_month(new_year, current.month)
        new_day = min(original_day, max_day)
        return date(new_year, current.month, new_day)

    def _days_in_month(self, year: int, month: int) -> int:
        if month in (1, 3, 5, 7, 8, 10, 12):
            return 31
        elif month in (4, 6, 9, 11):
            return 30
        elif month == 2:
            if self._is_leap_year(year):
                return 29
            return 28
        raise ValueError(f"Invalid month: {month}")

    def _is_leap_year(self, year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
