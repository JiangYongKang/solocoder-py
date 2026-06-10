import pytest

from solocoder_py.cron_scheduler import (
    CronParser,
    CronParseError,
    FieldType,
    InvalidFieldValueError,
    InvalidRangeError,
    InvalidStepError,
)


class TestCronParserBasic:
    def test_parse_every_minute(self):
        expr = CronParser.parse("* * * * *")
        assert len(expr.minute.values) == 60
        assert len(expr.hour.values) == 24
        assert len(expr.day_of_month.values) == 31
        assert len(expr.month.values) == 12
        assert len(expr.day_of_week.values) == 7

    def test_parse_preserves_raw_expression(self):
        raw = "30 9 * * 1-5"
        expr = CronParser.parse(raw)
        assert expr.raw == raw
        assert str(expr) == raw

    def test_parse_single_values(self):
        expr = CronParser.parse("30 14 15 6 3")
        assert expr.minute.values == {30}
        assert expr.hour.values == {14}
        assert expr.day_of_month.values == {15}
        assert expr.month.values == {6}
        assert expr.day_of_week.values == {3}

    def test_parse_field_order(self):
        expr = CronParser.parse("1 2 3 4 5")
        assert expr.minute.contains(1)
        assert expr.hour.contains(2)
        assert expr.day_of_month.contains(3)
        assert expr.month.contains(4)
        assert expr.day_of_week.contains(5)


class TestCronParserRanges:
    def test_parse_simple_range(self):
        expr = CronParser.parse("0 9-17 * * *")
        assert expr.hour.values == {9, 10, 11, 12, 13, 14, 15, 16, 17}

    def test_parse_range_full_range(self):
        expr = CronParser.parse("0-59 * * * *")
        assert len(expr.minute.values) == 60
        assert 0 in expr.minute.values
        assert 59 in expr.minute.values

    def test_parse_range_boundary(self):
        expr = CronParser.parse("* * 1-31 * *")
        assert len(expr.day_of_month.values) == 31
        assert 1 in expr.day_of_month.values
        assert 31 in expr.day_of_month.values

    def test_parse_range_single_element(self):
        expr = CronParser.parse("10-10 * * * *")
        assert expr.minute.values == {10}


class TestCronParserLists:
    def test_parse_comma_list(self):
        expr = CronParser.parse("0,15,30,45 * * * *")
        assert expr.minute.values == {0, 15, 30, 45}

    def test_parse_mixed_list_with_ranges(self):
        expr = CronParser.parse("0,5-10,30 * * * *")
        assert expr.minute.values == {0, 5, 6, 7, 8, 9, 10, 30}

    def test_parse_list_multiple_ranges(self):
        expr = CronParser.parse("* 9-12,14-17 * * *")
        assert expr.hour.values == {9, 10, 11, 12, 14, 15, 16, 17}

    def test_parse_list_disordered_values(self):
        expr = CronParser.parse("45,15,0,30 * * * *")
        assert expr.minute.values == {0, 15, 30, 45}


class TestCronParserStepValues:
    def test_parse_step_from_zero(self):
        expr = CronParser.parse("0/15 * * * *")
        assert expr.minute.values == {0, 15, 30, 45}

    def test_parse_step_from_start_value(self):
        expr = CronParser.parse("5/10 * * * *")
        assert expr.minute.values == {5, 15, 25, 35, 45, 55}

    def test_parse_step_with_star(self):
        expr = CronParser.parse("*/10 * * * *")
        assert expr.minute.values == {0, 10, 20, 30, 40, 50}

    def test_parse_step_with_range(self):
        expr = CronParser.parse("0-30/10 * * * *")
        assert expr.minute.values == {0, 10, 20, 30}

    def test_parse_step_hour_field(self):
        expr = CronParser.parse("0 */6 * * *")
        assert expr.hour.values == {0, 6, 12, 18}

    def test_parse_step_day_field(self):
        expr = CronParser.parse("0 0 */5 * *")
        assert expr.day_of_month.values == {1, 6, 11, 16, 21, 26, 31}

    def test_parse_step_every_two(self):
        expr = CronParser.parse("0 0 1-15/2 * *")
        assert expr.day_of_month.values == {1, 3, 5, 7, 9, 11, 13, 15}

    def test_parse_step_month_field(self):
        expr = CronParser.parse("0 0 1 */3 *")
        assert expr.month.values == {1, 4, 7, 10}

    def test_parse_step_exceeds_range_no_wrap(self):
        expr = CronParser.parse("50/15 * * * *")
        assert expr.minute.values == {50}


class TestCronParserMixedExpressions:
    def test_parse_weekday_work_hours(self):
        expr = CronParser.parse("0 9 * * 1-5")
        assert expr.minute.values == {0}
        assert expr.hour.values == {9}
        assert expr.day_of_week.values == {1, 2, 3, 4, 5}

    def test_parse_complex_expression(self):
        expr = CronParser.parse("0,30 8-18/2 1,15 * 0,6")
        assert expr.minute.values == {0, 30}
        assert expr.hour.values == {8, 10, 12, 14, 16, 18}
        assert expr.day_of_month.values == {1, 15}
        assert expr.day_of_week.values == {0, 6}

    def test_parse_monthly_quarterly(self):
        expr = CronParser.parse("0 0 1 1,4,7,10 *")
        assert expr.month.values == {1, 4, 7, 10}
        assert expr.day_of_month.values == {1}


class TestCronFieldProperties:
    def test_cron_field_min_max(self):
        expr = CronParser.parse("* * * * *")
        assert expr.minute.min_value == 0
        assert expr.minute.max_value == 59
        assert expr.hour.min_value == 0
        assert expr.hour.max_value == 23
        assert expr.day_of_month.min_value == 1
        assert expr.day_of_month.max_value == 31
        assert expr.month.min_value == 1
        assert expr.month.max_value == 12
        assert expr.day_of_week.min_value == 0
        assert expr.day_of_week.max_value == 6

    def test_cron_field_sorted_values(self):
        expr = CronParser.parse("45,0,30,15 * * * *")
        assert expr.minute.sorted_values() == [0, 15, 30, 45]

    def test_cron_field_contains(self):
        expr = CronParser.parse("0-30/5 * * * *")
        assert expr.minute.contains(0)
        assert expr.minute.contains(5)
        assert expr.minute.contains(30)
        assert not expr.minute.contains(35)

    def test_cron_field_len(self):
        expr = CronParser.parse("0,15,30,45 * * * *")
        assert len(expr.minute) == 4

    def test_cron_field_name(self):
        expr = CronParser.parse("* * * * *")
        assert expr.minute.name == "minute"
        assert expr.hour.name == "hour"
        assert expr.day_of_month.name == "day of month"
        assert expr.month.name == "month"
        assert expr.day_of_week.name == "day of week"

    def test_cron_field_next_value(self):
        expr = CronParser.parse("0,15,30,45 * * * *")
        assert expr.minute.next_value(0) == 0
        assert expr.minute.next_value(10) == 15
        assert expr.minute.next_value(50) is None
        assert expr.minute.next_value(15) == 15

    def test_cron_expression_fields_list(self):
        expr = CronParser.parse("1 2 3 4 5")
        fields = expr.fields
        assert len(fields) == 5
        assert fields[0].field_type == FieldType.MINUTE
        assert fields[1].field_type == FieldType.HOUR
        assert fields[2].field_type == FieldType.DAY_OF_MONTH
        assert fields[3].field_type == FieldType.MONTH
        assert fields[4].field_type == FieldType.DAY_OF_WEEK
