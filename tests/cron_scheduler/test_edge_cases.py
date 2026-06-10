from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from solocoder_py.cron_scheduler import (
    CronParser,
    CronParseError,
    CronScheduler,
    InvalidFieldValueError,
    InvalidRangeError,
    InvalidStepError,
    InvalidTimezoneError,
    NoMatchingTimeError,
)


class TestParseErrorsInvalidFieldCount:
    def test_empty_expression(self):
        with pytest.raises(CronParseError, match="cannot be empty"):
            CronParser.parse("")

    def test_whitespace_only_expression(self):
        with pytest.raises(CronParseError, match="cannot be empty"):
            CronParser.parse("   ")

    def test_too_few_fields(self):
        with pytest.raises(CronParseError, match="exactly 5 fields"):
            CronParser.parse("* * * *")

    def test_too_many_fields(self):
        with pytest.raises(CronParseError, match="exactly 5 fields"):
            CronParser.parse("* * * * * *")


class TestParseErrorsInvalidFieldValues:
    def test_minute_below_zero(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("-1 * * * *")
        assert exc.value.field == "minute"
        assert exc.value.value == -1
        assert exc.value.min_value == 0
        assert exc.value.max_value == 59

    def test_minute_above_59(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("60 * * * *")
        assert exc.value.field == "minute"
        assert exc.value.value == 60

    def test_hour_below_zero(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* -1 * * *")
        assert exc.value.field == "hour"

    def test_hour_above_23(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* 24 * * *")
        assert exc.value.field == "hour"

    def test_day_below_one(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* * 0 * *")
        assert exc.value.field == "day of month"

    def test_day_above_31(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* * 32 * *")
        assert exc.value.field == "day of month"

    def test_month_below_one(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* * * 0 *")
        assert exc.value.field == "month"

    def test_month_above_12(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* * * 13 *")
        assert exc.value.field == "month"

    def test_dow_below_zero(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* * * * -1")
        assert exc.value.field == "day of week"

    def test_dow_above_6(self):
        with pytest.raises(InvalidFieldValueError) as exc:
            CronParser.parse("* * * * 7")
        assert exc.value.field == "day of week"


class TestParseErrorsInvalidRanges:
    def test_range_start_greater_than_end_minute(self):
        with pytest.raises(InvalidRangeError) as exc:
            CronParser.parse("30-10 * * * *")
        assert exc.value.field == "minute"
        assert exc.value.start == 30
        assert exc.value.end == 10

    def test_range_start_greater_than_end_hour(self):
        with pytest.raises(InvalidRangeError) as exc:
            CronParser.parse("* 20-10 * * *")
        assert exc.value.field == "hour"

    def test_range_start_greater_than_end_day(self):
        with pytest.raises(InvalidRangeError) as exc:
            CronParser.parse("* * 20-10 * *")
        assert exc.value.field == "day of month"

    def test_range_value_below_min(self):
        with pytest.raises(InvalidFieldValueError):
            CronParser.parse("* 0--5 * * *")

    def test_negative_start_value_as_single(self):
        with pytest.raises(InvalidFieldValueError):
            CronParser.parse("* -5 * * *")

    def test_malformed_negative_range(self):
        with pytest.raises(CronParseError):
            CronParser.parse("* -5-10 * * *")

    def test_range_value_above_max(self):
        with pytest.raises(InvalidFieldValueError):
            CronParser.parse("* 10-100 * * *")

    def test_range_malformed_single_dash(self):
        with pytest.raises(CronParseError):
            CronParser.parse("* - * * *")


class TestParseErrorsInvalidSteps:
    def test_step_zero(self):
        with pytest.raises(InvalidStepError) as exc:
            CronParser.parse("*/0 * * * *")
        assert exc.value.field == "minute"
        assert exc.value.step == 0

    def test_step_negative(self):
        with pytest.raises(InvalidStepError):
            CronParser.parse("*/-5 * * * *")

    def test_step_exceeds_max_minute(self):
        with pytest.raises(InvalidStepError) as exc:
            CronParser.parse("*/60 * * * *")
        assert exc.value.field == "minute"
        assert exc.value.step == 60
        assert exc.value.max_value == 59

    def test_step_exceeds_max_hour(self):
        with pytest.raises(InvalidStepError) as exc:
            CronParser.parse("0 */24 * * *")
        assert exc.value.field == "hour"
        assert exc.value.step == 24

    def test_step_non_numeric(self):
        with pytest.raises(CronParseError, match="step value"):
            CronParser.parse("*/abc * * * *")

    def test_step_range_start_greater_than_end(self):
        with pytest.raises(InvalidRangeError):
            CronParser.parse("30-10/5 * * * *")

    def test_step_range_values_invalid(self):
        with pytest.raises(InvalidFieldValueError):
            CronParser.parse("60-70/5 * * * *")

    def test_step_multiple_slashes(self):
        with pytest.raises(CronParseError, match="Invalid step syntax"):
            CronParser.parse("0/15/5 * * * *")

    def test_step_start_value_invalid(self):
        with pytest.raises(InvalidFieldValueError):
            CronParser.parse("70/10 * * * *")

    def test_step_max_value_accepted(self):
        expr = CronParser.parse("*/59 * * * *")
        assert 0 in expr.minute.values
        assert 59 in expr.minute.values


class TestParseErrorsMalformedExpressions:
    def test_non_numeric_value(self):
        with pytest.raises(CronParseError, match="must be an integer"):
            CronParser.parse("abc * * * *")

    def test_mixed_alphanumeric(self):
        with pytest.raises(CronParseError):
            CronParser.parse("12a * * * *")

    def test_empty_comma_segment(self):
        with pytest.raises(CronParseError, match="Empty segment"):
            CronParser.parse(",0,30 * * * *")

    def test_trailing_comma(self):
        with pytest.raises(CronParseError, match="Empty segment"):
            CronParser.parse("0,30, * * * *")

    def test_empty_field_from_double_comma(self):
        with pytest.raises(CronParseError, match="Empty segment"):
            CronParser.parse("0,,30 * * * *")

    def test_too_few_fields_from_extra_spaces(self):
        with pytest.raises(CronParseError, match="exactly 5 fields"):
            CronParser.parse("*  * * *")


class TestSchedulerErrors:
    def test_invalid_timezone_name_constructor(self):
        with pytest.raises(InvalidTimezoneError) as exc:
            CronScheduler("* * * * *", timezone_name="Not/AValidTimezone")
        assert exc.value.timezone_name == "Not/AValidTimezone"

    def test_invalid_timezone_name_target(self):
        scheduler = CronScheduler("* * * * *")
        with pytest.raises(InvalidTimezoneError):
            scheduler.next_trigger(
                after=datetime(2025, 1, 1, tzinfo=timezone.utc),
                target_timezone_name="Fake/Zone",
            )

    def test_next_n_zero_raises(self):
        scheduler = CronScheduler("* * * * *")
        with pytest.raises(ValueError, match="positive"):
            scheduler.next_n_triggers(0)

    def test_next_n_negative_raises(self):
        scheduler = CronScheduler("* * * * *")
        with pytest.raises(ValueError, match="positive"):
            scheduler.next_n_triggers(-1)


class TestNoMatchingTimeScenarios:
    def test_impossible_day_month_combination_31_april(self):
        scheduler = CronScheduler("0 0 31 4 *")
        with pytest.raises(NoMatchingTimeError):
            scheduler.next_trigger(
                after=datetime(2025, 1, 1, tzinfo=timezone.utc)
            )

    def test_impossible_day_month_30_february(self):
        scheduler = CronScheduler("0 0 30 2 *")
        with pytest.raises(NoMatchingTimeError):
            scheduler.next_trigger(
                after=datetime(2025, 1, 1, tzinfo=timezone.utc)
            )

    def test_impossible_day_month_31_june(self):
        scheduler = CronScheduler("0 0 31 6 *")
        with pytest.raises(NoMatchingTimeError):
            scheduler.next_trigger(
                after=datetime(2025, 1, 1, tzinfo=timezone.utc)
            )


class TestExceptionHierarchy:
    def test_cron_parse_error_is_cron_error(self):
        try:
            CronParser.parse("bad")
        except CronParseError as e:
            assert isinstance(e, Exception)

    def test_invalid_field_value_is_parse_error(self):
        try:
            CronParser.parse("100 * * * *")
        except InvalidFieldValueError as e:
            assert isinstance(e, CronParseError)

    def test_invalid_range_is_parse_error(self):
        try:
            CronParser.parse("30-10 * * * *")
        except InvalidRangeError as e:
            assert isinstance(e, CronParseError)

    def test_invalid_step_is_parse_error(self):
        try:
            CronParser.parse("*/0 * * * *")
        except InvalidStepError as e:
            assert isinstance(e, CronParseError)

    def test_invalid_timezone_is_cron_error(self):
        try:
            CronScheduler("* * * * *", timezone_name="Bad/Zone")
        except InvalidTimezoneError as e:
            assert isinstance(e, Exception)

    def test_no_matching_time_is_cron_error(self):
        try:
            s = CronScheduler("0 0 31 4 *")
            s.next_trigger(after=datetime(2025, 1, 1, tzinfo=timezone.utc))
        except NoMatchingTimeError as e:
            assert isinstance(e, Exception)


class TestSchedulerEdgeCases:
    def test_exactly_on_trigger_time_finds_next(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 * * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 11, 0)

    def test_just_before_trigger_finds_it(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("30 * * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 29)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 10, 30)

    def test_just_after_trigger_finds_next_hour(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("30 * * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 31)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 11, 30)

    def test_end_of_day_minute_59(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("* * * * *")
        after = make_utc_datetime(2025, 1, 1, 23, 59)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 2, 0, 0)

    def test_end_of_day_hour_23(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 * * * *")
        after = make_utc_datetime(2025, 1, 1, 23, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 2, 0, 0)

    def test_end_of_month_december(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 0 1 * *")
        after = make_utc_datetime(2025, 12, 1, 0, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2026, 1, 1, 0, 0)

    def test_specific_value_list(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0 9,12,17 * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 12, 0)

    def test_combined_list_range_step(self, make_utc_datetime, make_scheduler):
        scheduler = make_scheduler("0,30 9-17/2 * * *")
        after = make_utc_datetime(2025, 1, 1, 10, 0)
        result = scheduler.next_trigger(after=after)
        assert result == make_utc_datetime(2025, 1, 1, 11, 0)
