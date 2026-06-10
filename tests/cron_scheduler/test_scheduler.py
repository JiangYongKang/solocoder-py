from datetime import datetime, timedelta, timezone

import pytest

from solocoder_py.cron_scheduler import CronScheduler

try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False

try:
    import tzdata  # noqa: F401
    HAS_TZDATA = True
except ImportError:
    HAS_TZDATA = False

NEEDS_TZDATA = pytest.mark.skipif(
    not (HAS_ZONEINFO and HAS_TZDATA),
    reason="zoneinfo with tzdata package is required for this test"
)


class TestBasicScheduling:
    def test_every_minute_next(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("* * * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 10, 1)

    def test_specific_minute_hour(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("30 14 * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 14, 30)

    def test_specific_time_passed_today(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("30 9 * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 2, 9, 30)

    def test_specific_minute_only(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("45 * * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 10, 45)


class TestStepScheduling:
    def test_step_minutes_from_zero(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0/15 * * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 10, 15)

    def test_step_minutes_from_offset(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("5/20 * * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 10, 5)

    def test_step_hours(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 */6 * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 12, 0)

    def test_step_days(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 */10 * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 11, 0, 0)


class TestWeekdayScheduling:
    def test_weekday_only(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 9 * * 1-5")
        after = make_utc_datetime(2025, 1, 4, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 6, 9, 0)

    def test_weekend_only(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 10 * * 0,6")
        after = make_utc_datetime(2025, 1, 6, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 11, 10, 0)

    def test_sunday_only(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 * * 0")
        after = make_utc_datetime(2025, 1, 7, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 12, 0, 0)

    def test_monday_only(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 * * 1")
        after = make_utc_datetime(2025, 1, 7, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 13, 0, 0)


class TestDayOfMonthScheduling:
    def test_specific_day_of_month(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 15 * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 15, 0, 0)

    def test_day_passed_this_month(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 10 * *")
        after = make_utc_datetime(2025, 1, 15, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 2, 10, 0, 0)

    def test_last_day_of_month_31(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 31 * *")
        after = make_utc_datetime(2025, 1, 30, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 31, 0, 0)

    def test_last_day_of_skips_short_months(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 31 * *")
        after = make_utc_datetime(2025, 1, 31, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 3, 31, 0, 0)


class TestMonthScheduling:
    def test_specific_month(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 1 6 *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 6, 1, 0, 0)

    def test_quarterly(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 1 */3 *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 4, 1, 0, 0)


class TestCrossYearBoundary:
    def test_new_year_eve_to_new_year(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 * * *")
        after = make_utc_datetime(2025, 12, 31, 23, 59)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2026, 1, 1, 0, 0)

    def test_year_end_month_rollover(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 1 * *")
        after = make_utc_datetime(2025, 12, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2026, 1, 1, 0, 0)

    def test_specific_date_next_year(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 1 1 *")
        after = make_utc_datetime(2025, 6, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2026, 1, 1, 0, 0)

    def test_december_to_january_month_range(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 1 12,1 *")
        after = make_utc_datetime(2025, 12, 2, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2026, 1, 1, 0, 0)


class TestLeapYearFebruary:
    def test_leap_year_feb_29_exists(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 29 2 *")
        after = make_utc_datetime(2024, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2024, 2, 29, 0, 0)

    def test_leap_year_feb_29_from_after(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 29 2 *")
        after = make_utc_datetime(2024, 3, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2028, 2, 29, 0, 0)

    def test_non_leap_year_skips_feb_29(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 29 2 *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2028, 2, 29, 0, 0)

    def test_feb_28_normal_year(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 28 2 *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 2, 28, 0, 0)

    def test_feb_28_leap_year(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 28 2 *")
        after = make_utc_datetime(2024, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2024, 2, 28, 0, 0)


class TestMonthLengthVariations:
    def test_30_day_month_31_not_present(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 31 * *")
        after = make_utc_datetime(2025, 3, 31, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 5, 31, 0, 0)

    def test_february_no_30(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 30 * *")
        after = make_utc_datetime(2025, 1, 30, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 3, 30, 0, 0)


class TestMultipleNextTriggers:
    def test_next_n_triggers_count(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 * * * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        results = scheduler.next_n_triggers(5, after=after)
        assert len(results) == 5
        for i, r in enumerate(results):
            assert r == make_utc_datetime(2025, 1, 1, i + 1, 0)

    def test_next_n_triggers_cross_day(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 23 * * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        results = scheduler.next_n_triggers(3, after=after)
        assert results[0] == make_utc_datetime(2025, 1, 1, 23, 0)
        assert results[1] == make_utc_datetime(2025, 1, 2, 23, 0)
        assert results[2] == make_utc_datetime(2025, 1, 3, 23, 0)


class TestDayOfWeekAndDayOfMonthCombined:
    def test_both_wildcard(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 9 * * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 9, 0)

    def test_only_weekday_set(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 9 * * 0")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 5, 9, 0)

    def test_only_day_set(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 9 15 * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 15, 9, 0)


class TestStepWrappingBehavior:
    def test_step_50_15_no_wrapping(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("50/15 * * * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 0, 50)

    def test_step_50_15_after_50_next_hour(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("50/15 * * * *")
        after = make_utc_datetime(2025, 1, 1, 0, 51)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 1, 50)


class TestPrecisionAndTimeNormalization:
    def test_result_truncated_to_minute(self, make_scheduler):
        scheduler = make_scheduler("* * * * *")
        after = datetime(2025, 1, 1, 10, 0, 30, tzinfo=timezone.utc)
        result = scheduler.next_trigger(after=after)
        assert result.second == 0
        assert result.microsecond == 0

    def test_seconds_ignored_finds_next_minute(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("* * * * *")
        after = datetime(2025, 1, 1, 10, 0, 0, 123456, tzinfo=timezone.utc)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 10, 1)


class TestTimezoneHandling:
    def test_utc_scheduler_naive_input(self, make_scheduler):
        scheduler = make_scheduler("0 9 * * *", timezone_name="UTC")
        after = datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result.tzinfo is not None
        assert result == datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)

    @NEEDS_TZDATA
    def test_scheduler_in_new_york_timezone(self, make_scheduler):
        scheduler = make_scheduler("0 9 * * *", timezone_name="America/New_York")
        after = datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc)
        result = scheduler.next_trigger(after=after)
        ny_tz = ZoneInfo("America/New_York")
        result_ny = result.astimezone(ny_tz)
        assert result_ny.hour == 9
        assert result_ny.minute == 0

    @NEEDS_TZDATA
    def test_target_timezone_conversion(self, make_scheduler):
        scheduler = make_scheduler("0 9 * * *", timezone_name="UTC")
        after = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        result = scheduler.next_trigger(
            after=after,
            target_timezone_name="America/New_York",
        )
        ny_tz = ZoneInfo("America/New_York")
        assert result.tzinfo == ny_tz
        expected_utc = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
        assert result == expected_utc.astimezone(ny_tz)

    @NEEDS_TZDATA
    def test_asia_tokyo_timezone(self, make_scheduler):
        scheduler = make_scheduler("0 9 * * *", timezone_name="Asia/Tokyo")
        after = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        result = scheduler.next_trigger(after=after)
        tokyo_tz = ZoneInfo("Asia/Tokyo")
        result_tokyo = result.astimezone(tokyo_tz)
        assert result_tokyo.hour == 9
        assert result_tokyo.minute == 0

    def test_default_uses_utc(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 12 * * *")
        after = make_utc_datetime(2025, 1, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 12, 0)

    def test_fixed_negative_offset_timezone(self, make_scheduler):
        scheduler = make_scheduler("0 9 * * *", timezone_name="UTC")
        after = datetime(2025, 1, 1, 14, 0, tzinfo=timezone(timedelta(hours=-5)))
        result = scheduler.next_trigger(after=after)
        assert result == datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)

    def test_fixed_positive_offset_timezone(self, make_scheduler):
        scheduler = make_scheduler("0 9 * * *", timezone_name="UTC")
        tokyo_offset = timezone(timedelta(hours=9))
        after = datetime(2025, 1, 1, 0, 0, tzinfo=tokyo_offset)
        result = scheduler.next_trigger(after=after)
        assert result == datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
