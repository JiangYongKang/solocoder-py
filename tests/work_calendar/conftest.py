from datetime import date, time

import pytest

from solocoder_py.work_calendar import (
    CalendarConfig,
    WorkCalendar,
    WorkDaySchedule,
    WorkTimeRange,
)


@pytest.fixture
def make_default_calendar():
    def _make() -> WorkCalendar:
        return WorkCalendar()
    return _make


@pytest.fixture
def make_spring_festival_calendar():
    def _make() -> WorkCalendar:
        holidays = [
            date(2024, 2, 10),
            date(2024, 2, 11),
            date(2024, 2, 12),
            date(2024, 2, 13),
            date(2024, 2, 14),
            date(2024, 2, 15),
            date(2024, 2, 16),
            date(2024, 2, 17),
        ]
        workdays = [
            date(2024, 2, 4),
            date(2024, 2, 18),
        ]
        config = CalendarConfig(
            holidays=frozenset(holidays),
            workdays=frozenset(workdays),
        )
        return WorkCalendar(config=config)
    return _make
