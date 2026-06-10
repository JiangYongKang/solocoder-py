from datetime import date, datetime, time

from solocoder_py.work_calendar import CalendarConfig, WorkCalendar, WorkDaySchedule, WorkTimeRange

from solocoder_py.sla_deadline import SlaTimer


def make_default_calendar() -> WorkCalendar:
    return WorkCalendar()


def make_calendar_with_holidays(holidays: list[date]) -> WorkCalendar:
    config = CalendarConfig(holidays=frozenset(holidays))
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


def make_default_sla_timer(total_work_hours: float = 8.0) -> SlaTimer:
    return SlaTimer(total_work_hours=total_work_hours)


def make_sla_timer_with_calendar(
    total_work_hours: float,
    calendar: WorkCalendar,
) -> SlaTimer:
    return SlaTimer(total_work_hours=total_work_hours, work_calendar=calendar)


def make_monday_9am() -> datetime:
    return datetime(2024, 1, 15, 9, 0, 0)


def make_monday_12pm() -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0)


def make_monday_1pm() -> datetime:
    return datetime(2024, 1, 15, 13, 0, 0)


def make_monday_6pm() -> datetime:
    return datetime(2024, 1, 15, 18, 0, 0)


def make_tuesday_9am() -> datetime:
    return datetime(2024, 1, 16, 9, 0, 0)


def make_friday_6pm() -> datetime:
    return datetime(2024, 1, 19, 18, 0, 0)


def make_saturday_9am() -> datetime:
    return datetime(2024, 1, 20, 9, 0, 0)


def make_monday_next_week_9am() -> datetime:
    return datetime(2024, 1, 22, 9, 0, 0)


def make_monday_10am() -> datetime:
    return datetime(2024, 1, 15, 10, 0, 0)


def make_monday_1030am() -> datetime:
    return datetime(2024, 1, 15, 10, 30, 0)


def make_monday_11am() -> datetime:
    return datetime(2024, 1, 15, 11, 0, 0)


def make_monday_1130am() -> datetime:
    return datetime(2024, 1, 15, 11, 30, 0)


def make_monday_3pm() -> datetime:
    return datetime(2024, 1, 15, 15, 0, 0)


def make_monday_4pm() -> datetime:
    return datetime(2024, 1, 15, 16, 0, 0)


def make_monday_930am() -> datetime:
    return datetime(2024, 1, 15, 9, 30, 0)
