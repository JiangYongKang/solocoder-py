from datetime import date, datetime, time

import pytest

from solocoder_py.work_calendar import (
    CalendarConfig,
    InvalidDurationError,
    InvalidWorkHoursError,
    WorkCalendar,
    WorkDaySchedule,
    WorkTimeRange,
)
from solocoder_py.work_calendar.exceptions import WorkCalendarError


class TestWorkTimeRange:
    def test_valid_range(self):
        r = WorkTimeRange(time(9, 0), time(18, 0))
        assert r.start == time(9, 0)
        assert r.end == time(18, 0)

    def test_invalid_range_raises_error(self):
        with pytest.raises(InvalidWorkHoursError):
            WorkTimeRange(time(18, 0), time(9, 0))

    def test_same_start_end_raises_error(self):
        with pytest.raises(InvalidWorkHoursError):
            WorkTimeRange(time(9, 0), time(9, 0))

    def test_duration_hours(self):
        r = WorkTimeRange(time(9, 0), time(12, 0))
        assert r.duration_hours == 3.0

        r2 = WorkTimeRange(time(13, 0), time(18, 0))
        assert r2.duration_hours == 5.0

    def test_contains(self):
        r = WorkTimeRange(time(9, 0), time(12, 0))
        assert r.contains(time(9, 0))
        assert r.contains(time(10, 30))
        assert r.contains(time(12, 0))
        assert not r.contains(time(8, 59))
        assert not r.contains(time(12, 1))


class TestWorkDaySchedule:
    def test_default_schedule(self):
        s = WorkDaySchedule()
        assert s.morning.start == time(9, 0)
        assert s.morning.end == time(12, 0)
        assert s.afternoon.start == time(13, 0)
        assert s.afternoon.end == time(18, 0)
        assert s.total_work_hours == 8.0

    def test_custom_schedule(self):
        s = WorkDaySchedule(
            morning=WorkTimeRange(time(8, 0), time(12, 0)),
            afternoon=WorkTimeRange(time(13, 30), time(17, 30)),
        )
        assert s.total_work_hours == 8.0

    def test_is_work_time(self):
        s = WorkDaySchedule()
        assert s.is_work_time(datetime(2024, 1, 15, 10, 0))
        assert s.is_work_time(datetime(2024, 1, 15, 14, 0))
        assert not s.is_work_time(datetime(2024, 1, 15, 12, 30))
        assert not s.is_work_time(datetime(2024, 1, 15, 8, 0))
        assert not s.is_work_time(datetime(2024, 1, 15, 19, 0))

    def test_get_work_periods(self):
        s = WorkDaySchedule()
        periods = s.get_work_periods()
        assert len(periods) == 2


class TestCalendarConfig:
    def test_default_config(self):
        config = CalendarConfig()
        assert len(config.holidays) == 0
        assert len(config.workdays) == 0

    def test_conflicting_dates_raise_error(self):
        with pytest.raises(ValueError):
            CalendarConfig(
                holidays=frozenset([date(2024, 1, 1)]),
                workdays=frozenset([date(2024, 1, 1)]),
            )


class TestWorkdayCheck:
    def test_weekday_is_workday(self, make_default_calendar):
        cal = make_default_calendar()
        assert cal.is_workday(date(2024, 1, 15))
        assert cal.is_workday(date(2024, 1, 16))
        assert cal.is_workday(date(2024, 1, 17))
        assert cal.is_workday(date(2024, 1, 18))
        assert cal.is_workday(date(2024, 1, 19))

    def test_weekend_is_not_workday(self, make_default_calendar):
        cal = make_default_calendar()
        assert not cal.is_workday(date(2024, 1, 13))
        assert not cal.is_workday(date(2024, 1, 14))

    def test_holiday_is_not_workday(self):
        cal = WorkCalendar(
            config=CalendarConfig(holidays=frozenset([date(2024, 1, 15)]))
        )
        assert not cal.is_workday(date(2024, 1, 15))

    def test_workday_on_weekend(self):
        cal = WorkCalendar(
            config=CalendarConfig(workdays=frozenset([date(2024, 1, 13)]))
        )
        assert cal.is_workday(date(2024, 1, 13))

    def test_workday_priority_over_holiday(self):
        cal = WorkCalendar(
            config=CalendarConfig(workdays=frozenset([date(2024, 1, 15)]))
        )
        assert cal.is_workday(date(2024, 1, 15))

    def test_holiday_priority_over_weekend_default(self):
        cal = WorkCalendar(
            config=CalendarConfig(holidays=frozenset([date(2024, 1, 15)]))
        )
        assert not cal.is_workday(date(2024, 1, 15))


class TestAddWorkDays:
    def test_zero_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2024, 1, 15), 0)
        assert result == date(2024, 1, 15)

    def test_positive_days_within_week(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2024, 1, 15), 3)
        assert result == date(2024, 1, 18)

    def test_positive_days_crossing_weekend(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2024, 1, 12), 3)
        assert result == date(2024, 1, 17)

    def test_negative_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2024, 1, 15), -3)
        assert result == date(2024, 1, 10)

    def test_negative_days_crossing_weekend(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2024, 1, 15), -5)
        assert result == date(2024, 1, 8)

    def test_with_holidays(self):
        cal = WorkCalendar(
            config=CalendarConfig(holidays=frozenset([date(2024, 1, 16)]))
        )
        result = cal.add_work_days(date(2024, 1, 15), 3)
        assert result == date(2024, 1, 19)

    def test_with_workdays_on_weekend(self):
        cal = WorkCalendar(
            config=CalendarConfig(workdays=frozenset([date(2024, 1, 13)]))
        )
        result = cal.add_work_days(date(2024, 1, 12), 3)
        assert result == date(2024, 1, 16)


class TestAddWorkHours:
    def test_zero_hours(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 10, 0), 0)
        assert result == datetime(2024, 1, 15, 10, 0)

    def test_negative_hours_raises_error(self, make_default_calendar):
        cal = make_default_calendar()
        with pytest.raises(InvalidDurationError):
            cal.add_work_hours(datetime(2024, 1, 15, 10, 0), -1)

    def test_within_morning_period(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 10, 0), 1)
        assert result == datetime(2024, 1, 15, 11, 0)

    def test_crossing_lunch_break(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 11, 0), 2)
        assert result == datetime(2024, 1, 15, 14, 0)

    def test_crossing_end_of_day(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 17, 0), 2)
        assert result == datetime(2024, 1, 16, 10, 0)

    def test_crossing_weekend(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 12, 17, 0), 2)
        assert result == datetime(2024, 1, 15, 10, 0)

    def test_full_day_of_work(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 9, 0), 8)
        assert result == datetime(2024, 1, 15, 18, 0)

    def test_more_than_one_day(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 9, 0), 10)
        assert result == datetime(2024, 1, 16, 11, 0)

    def test_start_before_work_hours(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 8, 0), 2)
        assert result == datetime(2024, 1, 15, 11, 0)

    def test_start_after_work_hours(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 20, 0), 2)
        assert result == datetime(2024, 1, 16, 11, 0)

    def test_start_during_lunch(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 12, 30), 2)
        assert result == datetime(2024, 1, 15, 15, 0)

    def test_with_holiday(self):
        cal = WorkCalendar(
            config=CalendarConfig(holidays=frozenset([date(2024, 1, 16)]))
        )
        result = cal.add_work_hours(datetime(2024, 1, 15, 17, 0), 2)
        assert result == datetime(2024, 1, 17, 10, 0)

    def test_with_workday_on_weekend(self):
        cal = WorkCalendar(
            config=CalendarConfig(workdays=frozenset([date(2024, 1, 13)]))
        )
        result = cal.add_work_hours(datetime(2024, 1, 12, 17, 0), 2)
        assert result == datetime(2024, 1, 13, 10, 0)

    def test_fractional_hours(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 9, 0), 1.5)
        assert result == datetime(2024, 1, 15, 10, 30)


class TestNaturalDaysToWorkDays:
    def test_zero_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.natural_days_to_work_days(date(2024, 1, 15), 0)
        assert result == 0

    def test_positive_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.natural_days_to_work_days(date(2024, 1, 12), 7)
        assert result == 5

    def test_negative_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.natural_days_to_work_days(date(2024, 1, 15), -7)
        assert result == -5

    def test_with_holidays(self):
        cal = WorkCalendar(
            config=CalendarConfig(holidays=frozenset([date(2024, 1, 15)]))
        )
        result = cal.natural_days_to_work_days(date(2024, 1, 12), 7)
        assert result == 4

    def test_with_workdays_on_weekend(self):
        cal = WorkCalendar(
            config=CalendarConfig(workdays=frozenset([date(2024, 1, 13)]))
        )
        result = cal.natural_days_to_work_days(date(2024, 1, 12), 7)
        assert result == 6


class TestWorkDaysToNaturalDays:
    def test_zero_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.work_days_to_natural_days(date(2024, 1, 15), 0)
        assert result == 0

    def test_positive_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.work_days_to_natural_days(date(2024, 1, 12), 5)
        assert result == 7

    def test_negative_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.work_days_to_natural_days(date(2024, 1, 15), -5)
        assert result == -7

    def test_with_holidays(self):
        cal = WorkCalendar(
            config=CalendarConfig(holidays=frozenset([date(2024, 1, 15)]))
        )
        result = cal.work_days_to_natural_days(date(2024, 1, 12), 4)
        assert result == 7

    def test_with_workdays_on_weekend(self):
        cal = WorkCalendar(
            config=CalendarConfig(workdays=frozenset([date(2024, 1, 13)]))
        )
        result = cal.work_days_to_natural_days(date(2024, 1, 12), 6)
        assert result == 7


class TestCountWorkDaysInRange:
    def test_same_day_workday(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.count_work_days_in_range(date(2024, 1, 15), date(2024, 1, 15))
        assert result == 1

    def test_same_day_weekend(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.count_work_days_in_range(date(2024, 1, 13), date(2024, 1, 13))
        assert result == 0

    def test_one_week(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.count_work_days_in_range(date(2024, 1, 8), date(2024, 1, 14))
        assert result == 5

    def test_reversed_dates(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.count_work_days_in_range(date(2024, 1, 14), date(2024, 1, 8))
        assert result == 5


class TestGetWorkdaysBetween:
    def test_empty_range(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.get_workdays_between(date(2024, 1, 13), date(2024, 1, 14))
        assert len(result) == 0

    def test_one_week(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.get_workdays_between(date(2024, 1, 8), date(2024, 1, 14))
        assert len(result) == 5
        assert date(2024, 1, 8) in result
        assert date(2024, 1, 12) in result
        assert date(2024, 1, 13) not in result

    def test_reversed_dates(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.get_workdays_between(date(2024, 1, 14), date(2024, 1, 8))
        assert len(result) == 5


class TestSpringFestivalEdgeCase:
    def test_long_holiday_workday_check(self, make_spring_festival_calendar):
        cal = make_spring_festival_calendar()
        assert not cal.is_workday(date(2024, 2, 10))
        assert not cal.is_workday(date(2024, 2, 11))
        assert not cal.is_workday(date(2024, 2, 12))
        assert not cal.is_workday(date(2024, 2, 13))
        assert not cal.is_workday(date(2024, 2, 14))
        assert not cal.is_workday(date(2024, 2, 15))
        assert not cal.is_workday(date(2024, 2, 16))
        assert not cal.is_workday(date(2024, 2, 17))
        assert cal.is_workday(date(2024, 2, 18))

    def test_workday_before_holiday(self, make_spring_festival_calendar):
        cal = make_spring_festival_calendar()
        assert cal.is_workday(date(2024, 2, 9))
        assert cal.is_workday(date(2024, 2, 4))

    def test_add_work_days_through_holiday(self, make_spring_festival_calendar):
        cal = make_spring_festival_calendar()
        result = cal.add_work_days(date(2024, 2, 9), 2)
        assert result == date(2024, 2, 19)

    def test_add_work_hours_through_holiday(self, make_spring_festival_calendar):
        cal = make_spring_festival_calendar()
        result = cal.add_work_hours(datetime(2024, 2, 9, 17, 0), 2)
        assert result == datetime(2024, 2, 18, 10, 0)


class TestYearBoundary:
    def test_add_work_days_cross_year(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2024, 12, 31), 2)
        assert result == date(2025, 1, 2)

    def test_add_work_days_cross_year_backward(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2025, 1, 2), -2)
        assert result == date(2024, 12, 31)

    def test_add_work_hours_cross_year(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 12, 31, 17, 0), 2)
        assert result == datetime(2025, 1, 1, 10, 0)


class TestEmptyHolidayConfig:
    def test_empty_holidays_workday_check(self, make_default_calendar):
        cal = make_default_calendar()
        assert cal.is_workday(date(2024, 1, 15))
        assert not cal.is_workday(date(2024, 1, 13))

    def test_empty_holidays_add_days(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_days(date(2024, 1, 12), 3)
        assert result == date(2024, 1, 17)

    def test_set_holidays_after_init(self):
        cal = WorkCalendar()
        assert cal.is_workday(date(2024, 1, 15))
        cal.set_holidays([date(2024, 1, 15)])
        assert not cal.is_workday(date(2024, 1, 15))

    def test_set_workdays_after_init(self):
        cal = WorkCalendar()
        assert not cal.is_workday(date(2024, 1, 13))
        cal.set_workdays([date(2024, 1, 13)])
        assert cal.is_workday(date(2024, 1, 13))

    def test_set_conflicting_dates_raises_error(self):
        cal = WorkCalendar()
        cal.set_holidays([date(2024, 1, 15)])
        with pytest.raises(ValueError):
            cal.set_workdays([date(2024, 1, 15)])

    def test_set_work_schedule(self):
        cal = WorkCalendar()
        new_schedule = WorkDaySchedule(
            morning=WorkTimeRange(time(8, 0), time(12, 0)),
            afternoon=WorkTimeRange(time(13, 0), time(17, 0)),
        )
        cal.set_work_schedule(new_schedule)
        result = cal.add_work_hours(datetime(2024, 1, 15, 8, 0), 8)
        assert result == datetime(2024, 1, 15, 17, 0)


class TestAllHolidaysScenario:
    def test_all_holidays_workday_check(self):
        holidays = [date(2024, 1, d) for d in range(1, 32)]
        cal = WorkCalendar(config=CalendarConfig(holidays=frozenset(holidays)))
        for d in range(1, 32):
            assert not cal.is_workday(date(2024, 1, d))

    def test_count_work_days_in_all_holiday_range(self):
        holidays = [date(2024, 1, d) for d in range(1, 32)]
        cal = WorkCalendar(config=CalendarConfig(holidays=frozenset(holidays)))
        result = cal.count_work_days_in_range(date(2024, 1, 1), date(2024, 1, 31))
        assert result == 0


class TestLongWorkHours:
    def test_very_long_work_hours(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 9, 0), 80)
        assert result == datetime(2024, 1, 26, 18, 0)

    def test_40_hours_one_work_week(self, make_default_calendar):
        cal = make_default_calendar()
        result = cal.add_work_hours(datetime(2024, 1, 15, 9, 0), 40)
        assert result == datetime(2024, 1, 19, 18, 0)


class TestExceptions:
    def test_invalid_duration_error_is_work_calendar_error(self):
        assert issubclass(InvalidDurationError, WorkCalendarError)

    def test_invalid_work_hours_error_is_work_calendar_error(self):
        assert issubclass(InvalidWorkHoursError, WorkCalendarError)


@pytest.fixture
def make_default_calendar():
    def _make():
        return WorkCalendar()
    return _make


@pytest.fixture
def make_spring_festival_calendar():
    def _make():
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
