from __future__ import annotations

import calendar
from datetime import date, timedelta
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

    @staticmethod
    def _advance(current: date, frequency: Frequency, interval: int, original_day: int) -> date:
        if frequency == Frequency.DAILY:
            return RRuleExpander._add_days(current, interval)
        elif frequency == Frequency.WEEKLY:
            return RRuleExpander._add_days(current, interval * 7)
        elif frequency == Frequency.MONTHLY:
            return RRuleExpander._add_months(current, interval, original_day)
        elif frequency == Frequency.YEARLY:
            return RRuleExpander._add_years(current, interval, original_day)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")

    @staticmethod
    def _add_days(current: date, days: int) -> date:
        return current + timedelta(days=days)

    @staticmethod
    def _add_months(current: date, months: int, original_day: int) -> date:
        total_months = current.year * 12 + current.month - 1 + months
        new_year = total_months // 12
        new_month = total_months % 12 + 1
        max_day = calendar.monthrange(new_year, new_month)[1]
        new_day = min(original_day, max_day)
        return date(new_year, new_month, new_day)

    @staticmethod
    def _add_years(current: date, years: int, original_day: int) -> date:
        new_year = current.year + years
        max_day = calendar.monthrange(new_year, current.month)[1]
        new_day = min(original_day, max_day)
        return date(new_year, current.month, new_day)
