from datetime import date

import pytest

from solocoder_py.rrule import (
    Frequency,
    InvalidCountError,
    InvalidDateRangeError,
    InvalidFrequencyError,
    InvalidIntervalError,
    MissingTerminationConditionError,
    RRule,
    RRuleExpander,
)

from .conftest import make_date, make_dates


class TestFrequencyEnum:
    def test_frequency_values(self):
        assert Frequency.DAILY == "DAILY"
        assert Frequency.WEEKLY == "WEEKLY"
        assert Frequency.MONTHLY == "MONTHLY"
        assert Frequency.YEARLY == "YEARLY"

    def test_frequency_members(self):
        members = list(Frequency)
        assert len(members) == 4
        assert Frequency.DAILY in members
        assert Frequency.WEEKLY in members
        assert Frequency.MONTHLY in members
        assert Frequency.YEARLY in members


class TestRRuleModel:
    def test_rrule_creation_minimal(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=5,
        )
        assert rule.frequency == Frequency.DAILY
        assert rule.start_date == make_date(2026, 1, 1)
        assert rule.interval == 1
        assert rule.count == 5
        assert rule.end_date is None
        assert rule.exdates == set()

    def test_rrule_creation_with_end_date(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 1, 1),
            end_date=make_date(2026, 12, 31),
        )
        assert rule.end_date == make_date(2026, 12, 31)
        assert rule.count is None

    def test_rrule_creation_with_interval(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 1, 1),
            interval=3,
            count=4,
        )
        assert rule.interval == 3

    def test_rrule_creation_with_exdates(self):
        exdates = {make_date(2026, 1, 3), make_date(2026, 1, 5)}
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=10,
            exdates=exdates,
        )
        assert rule.exdates == exdates

    def test_rrule_creation_both_count_and_end_date(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=100,
            end_date=make_date(2026, 1, 31),
        )
        assert rule.count == 100
        assert rule.end_date == make_date(2026, 1, 31)

    def test_rrule_exdates_converted_to_set(self):
        exdates_list = [make_date(2026, 1, 3), make_date(2026, 1, 3), make_date(2026, 1, 5)]
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=10,
            exdates=exdates_list,
        )
        assert isinstance(rule.exdates, set)
        assert len(rule.exdates) == 2


class TestRRuleModelValidationErrors:
    def test_invalid_frequency_raises(self):
        with pytest.raises(InvalidFrequencyError):
            RRule(
                frequency="INVALID",
                start_date=make_date(2026, 1, 1),
                count=5,
            )

    def test_interval_zero_raises(self):
        with pytest.raises(InvalidIntervalError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 1),
                interval=0,
                count=5,
            )

    def test_interval_negative_raises(self):
        with pytest.raises(InvalidIntervalError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 1),
                interval=-1,
                count=5,
            )

    def test_interval_non_integer_raises(self):
        with pytest.raises(InvalidIntervalError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 1),
                interval=1.5,
                count=5,
            )

    def test_count_zero_raises(self):
        with pytest.raises(InvalidCountError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 1),
                count=0,
            )

    def test_count_negative_raises(self):
        with pytest.raises(InvalidCountError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 1),
                count=-5,
            )

    def test_count_non_integer_raises(self):
        with pytest.raises(InvalidCountError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 1),
                count=5.5,
            )

    def test_start_date_after_end_date_raises(self):
        with pytest.raises(InvalidDateRangeError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 10),
                end_date=make_date(2026, 1, 1),
            )

    def test_no_count_and_no_end_date_raises(self):
        with pytest.raises(MissingTerminationConditionError):
            RRule(
                frequency=Frequency.DAILY,
                start_date=make_date(2026, 1, 1),
            )


class TestDailyExpansion:
    def setup_method(self):
        self.expander = RRuleExpander()

    def test_daily_basic(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=5,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 2), (2026, 1, 3), (2026, 1, 4), (2026, 1, 5),
        ])
        assert result == expected

    def test_daily_with_interval(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            interval=3,
            count=4,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 4), (2026, 1, 7), (2026, 1, 10),
        ])
        assert result == expected

    def test_daily_with_end_date(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 28),
            end_date=make_date(2026, 2, 3),
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 28), (2026, 1, 29), (2026, 1, 30), (2026, 1, 31),
            (2026, 2, 1), (2026, 2, 2), (2026, 2, 3),
        ])
        assert result == expected

    def test_daily_count_and_end_date_count_wins(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=3,
            end_date=make_date(2026, 1, 10),
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 1), (2026, 1, 2), (2026, 1, 3)])
        assert result == expected

    def test_daily_count_and_end_date_end_date_wins(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=100,
            end_date=make_date(2026, 1, 3),
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 1), (2026, 1, 2), (2026, 1, 3)])
        assert result == expected


class TestWeeklyExpansion:
    def setup_method(self):
        self.expander = RRuleExpander()

    def test_weekly_basic(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 1, 1),
            count=4,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 8), (2026, 1, 15), (2026, 1, 22),
        ])
        assert result == expected

    def test_weekly_with_interval(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 1, 1),
            interval=2,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 15), (2026, 1, 29),
        ])
        assert result == expected

    def test_weekly_cross_month(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 1, 20),
            count=4,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 20), (2026, 1, 27), (2026, 2, 3), (2026, 2, 10),
        ])
        assert result == expected

    def test_weekly_with_end_date(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 1, 1),
            end_date=make_date(2026, 1, 20),
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 8), (2026, 1, 15),
        ])
        assert result == expected


class TestMonthlyExpansion:
    def setup_method(self):
        self.expander = RRuleExpander()

    def test_monthly_basic(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 1, 15),
            count=5,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 15), (2026, 2, 15), (2026, 3, 15), (2026, 4, 15), (2026, 5, 15),
        ])
        assert result == expected

    def test_monthly_with_interval(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 1, 1),
            interval=3,
            count=4,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 4, 1), (2026, 7, 1), (2026, 10, 1),
        ])
        assert result == expected

    def test_monthly_end_of_month_adjustment(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 1, 31),
            count=6,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 31), (2026, 2, 28), (2026, 3, 31), (2026, 4, 30),
            (2026, 5, 31), (2026, 6, 30),
        ])
        assert result == expected

    def test_monthly_cross_year(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 11, 15),
            count=4,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 11, 15), (2026, 12, 15), (2027, 1, 15), (2027, 2, 15),
        ])
        assert result == expected

    def test_monthly_leap_year_february(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2024, 1, 31),
            count=2,
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2024, 1, 31), (2024, 2, 29)])
        assert result == expected


class TestYearlyExpansion:
    def setup_method(self):
        self.expander = RRuleExpander()

    def test_yearly_basic(self):
        rule = RRule(
            frequency=Frequency.YEARLY,
            start_date=make_date(2026, 6, 15),
            count=4,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 6, 15), (2027, 6, 15), (2028, 6, 15), (2029, 6, 15),
        ])
        assert result == expected

    def test_yearly_with_interval(self):
        rule = RRule(
            frequency=Frequency.YEARLY,
            start_date=make_date(2026, 1, 1),
            interval=5,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2031, 1, 1), (2036, 1, 1),
        ])
        assert result == expected

    def test_yearly_leap_year_feb_29(self):
        rule = RRule(
            frequency=Frequency.YEARLY,
            start_date=make_date(2024, 2, 29),
            count=4,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2024, 2, 29), (2025, 2, 28), (2026, 2, 28), (2027, 2, 28),
        ])
        assert result == expected

    def test_yearly_leap_year_cycle(self):
        rule = RRule(
            frequency=Frequency.YEARLY,
            start_date=make_date(2024, 2, 29),
            interval=4,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2024, 2, 29), (2028, 2, 29), (2032, 2, 29),
        ])
        assert result == expected

    def test_yearly_century_year_not_leap(self):
        rule = RRule(
            frequency=Frequency.YEARLY,
            start_date=make_date(2000, 2, 29),
            interval=100,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2000, 2, 29), (2100, 2, 28), (2200, 2, 28),
        ])
        assert result == expected


class TestExclusionDates:
    def setup_method(self):
        self.expander = RRuleExpander()

    def test_exdates_basic(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=5,
            exdates={make_date(2026, 1, 3)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 2), (2026, 1, 4), (2026, 1, 5), (2026, 1, 6),
        ])
        assert result == expected

    def test_exdates_multiple(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=4,
            exdates={make_date(2026, 1, 2), make_date(2026, 1, 4), make_date(2026, 1, 5)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 3), (2026, 1, 6), (2026, 1, 7),
        ])
        assert result == expected

    def test_exdates_not_counted(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=3,
            exdates={make_date(2026, 1, 1), make_date(2026, 1, 2)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 3), (2026, 1, 4), (2026, 1, 5)])
        assert result == expected
        assert len(result) == 3

    def test_exdates_start_date_excluded(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=3,
            exdates={make_date(2026, 1, 1)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 2), (2026, 1, 3), (2026, 1, 4)])
        assert result == expected

    def test_exdates_with_end_date(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            end_date=make_date(2026, 1, 5),
            exdates={make_date(2026, 1, 2), make_date(2026, 1, 4)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 1), (2026, 1, 3), (2026, 1, 5)])
        assert result == expected

    def test_exdates_all_dates_within_range(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=3,
            exdates={
                make_date(2026, 1, 1), make_date(2026, 1, 2), make_date(2026, 1, 3),
                make_date(2026, 1, 4), make_date(2026, 1, 5),
            },
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 6), (2026, 1, 7), (2026, 1, 8)])
        assert result == expected

    def test_exdates_with_weekly(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 1, 1),
            count=3,
            exdates={make_date(2026, 1, 8)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 1), (2026, 1, 15), (2026, 1, 22)])
        assert result == expected


class TestBoundaryConditions:
    def setup_method(self):
        self.expander = RRuleExpander()

    def test_start_date_equals_end_date(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            end_date=make_date(2026, 1, 1),
        )
        result = self.expander.expand(rule)
        expected = [make_date(2026, 1, 1)]
        assert result == expected

    def test_start_date_equals_end_date_with_exdate(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            end_date=make_date(2026, 1, 1),
            exdates={make_date(2026, 1, 1)},
        )
        result = self.expander.expand(rule)
        assert result == []

    def test_count_one(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 6, 15),
            count=1,
        )
        result = self.expander.expand(rule)
        expected = [make_date(2026, 6, 15)]
        assert result == expected

    def test_interval_large_value(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            interval=30,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([(2026, 1, 1), (2026, 1, 31), (2026, 3, 2)])
        assert result == expected

    def test_daily_cross_year_boundary(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 12, 29),
            count=5,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 12, 29), (2026, 12, 30), (2026, 12, 31),
            (2027, 1, 1), (2027, 1, 2),
        ])
        assert result == expected

    def test_weekly_cross_year_boundary(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 12, 20),
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 12, 20), (2026, 12, 27), (2027, 1, 3),
        ])
        assert result == expected

    def test_monthly_large_interval_cross_years(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 1, 15),
            interval=18,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 15), (2027, 7, 15), (2029, 1, 15),
        ])
        assert result == expected

    def test_all_generated_dates_excluded(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            end_date=make_date(2026, 1, 5),
            exdates={
                make_date(2026, 1, 1), make_date(2026, 1, 2), make_date(2026, 1, 3),
                make_date(2026, 1, 4), make_date(2026, 1, 5),
            },
        )
        result = self.expander.expand(rule)
        assert result == []

    def test_exdates_with_large_interval(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            interval=7,
            count=4,
            exdates={make_date(2026, 1, 15)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 8), (2026, 1, 22), (2026, 1, 29),
        ])
        assert result == expected

    def test_end_date_before_next_interval(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            interval=5,
            end_date=make_date(2026, 1, 4),
        )
        result = self.expander.expand(rule)
        expected = [make_date(2026, 1, 1)]
        assert result == expected


class TestRRuleExpanderEdgeCases:
    def setup_method(self):
        self.expander = RRuleExpander()

    def test_expander_reuse(self):
        rule1 = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=3,
        )
        result1 = self.expander.expand(rule1)

        rule2 = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 1, 1),
            count=2,
        )
        result2 = self.expander.expand(rule2)

        assert result1 == make_dates([(2026, 1, 1), (2026, 1, 2), (2026, 1, 3)])
        assert result2 == make_dates([(2026, 1, 1), (2026, 1, 8)])

    def test_daily_advance_across_months(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 28),
            count=6,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 28), (2026, 1, 29), (2026, 1, 30), (2026, 1, 31),
            (2026, 2, 1), (2026, 2, 2),
        ])
        assert result == expected

    def test_daily_advance_large_days(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 15),
            interval=45,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 15), (2026, 3, 1), (2026, 4, 15),
        ])
        assert result == expected

    def test_weekly_advance_across_year(self):
        rule = RRule(
            frequency=Frequency.WEEKLY,
            start_date=make_date(2026, 12, 15),
            interval=3,
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 12, 15), (2027, 1, 5), (2027, 1, 26),
        ])
        assert result == expected

    def test_monthly_advance_december(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 12, 10),
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 12, 10), (2027, 1, 10), (2027, 2, 10),
        ])
        assert result == expected

    def test_yearly_century_leap_year(self):
        rule = RRule(
            frequency=Frequency.YEARLY,
            start_date=make_date(1996, 2, 29),
            count=3,
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (1996, 2, 29), (1997, 2, 28), (1998, 2, 28),
        ])
        assert result == expected

    def test_exdates_with_end_date_and_count(self):
        rule = RRule(
            frequency=Frequency.DAILY,
            start_date=make_date(2026, 1, 1),
            count=10,
            end_date=make_date(2026, 1, 10),
            exdates={make_date(2026, 1, 5)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 1), (2026, 1, 2), (2026, 1, 3), (2026, 1, 4),
            (2026, 1, 6), (2026, 1, 7), (2026, 1, 8), (2026, 1, 9), (2026, 1, 10),
        ])
        assert result == expected
        assert len(result) == 9

    def test_exdates_with_monthly_end_of_month(self):
        rule = RRule(
            frequency=Frequency.MONTHLY,
            start_date=make_date(2026, 1, 31),
            count=4,
            exdates={make_date(2026, 2, 28)},
        )
        result = self.expander.expand(rule)
        expected = make_dates([
            (2026, 1, 31), (2026, 3, 31), (2026, 4, 30), (2026, 5, 31),
        ])
        assert result == expected
