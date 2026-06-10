from datetime import date, datetime, time

from solocoder_py.work_calendar import (
    CalendarConfig,
    WorkCalendar,
    WorkDaySchedule,
    WorkTimeRange,
)


def make_default_calendar() -> WorkCalendar:
    return WorkCalendar()


def make_calendar_with_holidays(holidays: list[date]) -> WorkCalendar:
    config = CalendarConfig(holidays=frozenset(holidays))
    return WorkCalendar(config=config)


def make_calendar_with_workdays(workdays: list[date]) -> WorkCalendar:
    config = CalendarConfig(workdays=frozenset(workdays))
    return WorkCalendar(config=config)


def make_calendar_with_custom_schedule(
    morning_start: int = 9,
    morning_end: int = 12,
    afternoon_start: int = 13,
    afternoon_end: int = 18,
) -> WorkCalendar:
    schedule = WorkDaySchedule(
        morning=WorkTimeRange(time(morning_start, 0), time(morning_end, 0)),
        afternoon=WorkTimeRange(time(afternoon_start, 0), time(afternoon_end, 0)),
    )
    config = CalendarConfig(work_schedule=schedule)
    return WorkCalendar(config=config)


def make_spring_festival_calendar() -> WorkCalendar:
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
