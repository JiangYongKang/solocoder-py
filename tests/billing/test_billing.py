from datetime import datetime, timedelta

import pytest

from solocoder_py.billing import (
    BillingEngine,
    BillingError,
    BillingPeriodStatus,
    FutureUsageError,
    InvalidPeriodError,
    InvalidTierConfigError,
    PeriodSettledError,
    PricingNotFoundError,
    PricingTier,
    ResourceNotFoundError,
)

from .conftest import (
    build_engine_with_single_tier,
    build_engine_with_three_tiers,
    in_period,
    make_simple_tier,
    make_three_tiers,
    open_standard_period,
)


ACC = "acc-001"
RES = "storage"


class TestUsageAccumulation:
    def test_report_and_query_usage(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 10, reported_at=in_period(period, 1))
        assert engine.get_current_usage(ACC, RES) == 10

        engine.report_usage(ACC, RES, 20, reported_at=in_period(period, 5))
        assert engine.get_current_usage(ACC, RES) == 30

    def test_usage_isolated_per_account(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        engine.report_usage("acc-a", RES, 10, reported_at=in_period(period, 1))
        engine.report_usage("acc-b", RES, 50, reported_at=in_period(period, 2))

        assert engine.get_current_usage("acc-a", RES) == 10
        assert engine.get_current_usage("acc-b", RES) == 50
        assert engine.get_current_usage("acc-c", RES) == 0

    def test_usage_isolated_per_resource(self):
        engine = BillingEngine()
        from .conftest import DEFAULT_EFFECTIVE_FROM
        engine.configure_tiered_pricing("cpu", make_simple_tier(1.0), effective_from=DEFAULT_EFFECTIVE_FROM)
        engine.configure_tiered_pricing("memory", make_simple_tier(2.0), effective_from=DEFAULT_EFFECTIVE_FROM)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, "cpu", 10, reported_at=in_period(period, 1))
        engine.report_usage(ACC, "memory", 5, reported_at=in_period(period, 2))

        assert engine.get_current_usage(ACC, "cpu") == 10
        assert engine.get_current_usage(ACC, "memory") == 5


class TestSingleTierPricing:
    def test_single_tier_flat_rate(self):
        engine = build_engine_with_single_tier(RES, 2.5)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 100, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        assert RES in estimates
        assert estimates[RES].total_cost == pytest.approx(250.0)

    def test_zero_usage_costs_zero(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        open_standard_period(engine)

        estimates = engine.estimate_current_cost(ACC)
        assert RES not in estimates


class TestMultiTierPricing:
    def test_three_tiers_first_tier_only(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 50, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        assert estimates[RES].total_cost == pytest.approx(50.0)

    def test_three_tiers_first_and_second(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 300, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        expected = 100 * 1.0 + 200 * 0.8
        assert estimates[RES].total_cost == pytest.approx(expected)

    def test_three_tiers_all_three(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 1000, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        expected = 100 * 1.0 + 400 * 0.8 + 500 * 0.6
        assert estimates[RES].total_cost == pytest.approx(expected)

    def test_tier_details_are_present(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 300, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        line = estimates[RES]
        assert len(line.proportional_splits) == 1
        split = line.proportional_splits[0]
        assert len(split.tier_details) == 2

        first_tier = split.tier_details[0]
        assert first_tier.tier_min == 0
        assert first_tier.tier_max == 100
        assert first_tier.unit_price == 1.0
        assert first_tier.units_applied == pytest.approx(100)
        assert first_tier.tier_cost == pytest.approx(100.0)

        second_tier = split.tier_details[1]
        assert second_tier.tier_min == 100
        assert second_tier.tier_max == 500
        assert second_tier.unit_price == 0.8
        assert second_tier.units_applied == pytest.approx(200)
        assert second_tier.tier_cost == pytest.approx(160.0)


class TestTierBoundaryConditions:
    def test_usage_exactly_at_first_boundary(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 100, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        assert estimates[RES].total_cost == pytest.approx(100 * 1.0)

    def test_usage_exactly_at_second_boundary(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 500, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        expected = 100 * 1.0 + 400 * 0.8
        assert estimates[RES].total_cost == pytest.approx(expected)

    def test_one_unit_into_second_tier(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 101, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        expected = 100 * 1.0 + 1 * 0.8
        assert estimates[RES].total_cost == pytest.approx(expected)

    def test_one_unit_into_third_tier(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 501, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)
        expected = 100 * 1.0 + 400 * 0.8 + 1 * 0.6
        assert estimates[RES].total_cost == pytest.approx(expected)

    def test_zero_usage(self):
        engine = build_engine_with_three_tiers(RES)
        open_standard_period(engine)

        estimates = engine.estimate_current_cost(ACC)
        assert RES not in estimates


class TestTierConfigValidation:
    def test_empty_tiers_raises(self):
        with pytest.raises(InvalidTierConfigError):
            from solocoder_py.billing import TieredPricing
            TieredPricing(resource_type=RES, tiers=[])

    def test_first_tier_not_starting_at_zero_raises(self):
        with pytest.raises(InvalidTierConfigError):
            from solocoder_py.billing import TieredPricing
            TieredPricing(
                resource_type=RES,
                tiers=[PricingTier(min_units=10, max_units=100, unit_price=1.0)],
            )

    def test_tiers_not_contiguous_gap_raises(self):
        with pytest.raises(InvalidTierConfigError):
            from solocoder_py.billing import TieredPricing
            TieredPricing(
                resource_type=RES,
                tiers=[
                    PricingTier(min_units=0, max_units=100, unit_price=1.0),
                    PricingTier(min_units=200, max_units=500, unit_price=0.8),
                ],
            )

    def test_tiers_overlap_raises(self):
        with pytest.raises(InvalidTierConfigError):
            from solocoder_py.billing import TieredPricing
            TieredPricing(
                resource_type=RES,
                tiers=[
                    PricingTier(min_units=0, max_units=100, unit_price=1.0),
                    PricingTier(min_units=50, max_units=200, unit_price=0.8),
                ],
            )

    def test_middle_tier_unbounded_raises(self):
        with pytest.raises(InvalidTierConfigError):
            from solocoder_py.billing import TieredPricing
            TieredPricing(
                resource_type=RES,
                tiers=[
                    PricingTier(min_units=0, max_units=None, unit_price=1.0),
                    PricingTier(min_units=100, max_units=500, unit_price=0.8),
                ],
            )

    def test_negative_unit_price_raises(self):
        with pytest.raises(InvalidTierConfigError):
            PricingTier(min_units=0, max_units=100, unit_price=-1.0)

    def test_negative_min_units_raises(self):
        with pytest.raises(InvalidTierConfigError):
            PricingTier(min_units=-1, max_units=100, unit_price=1.0)

    def test_max_units_not_greater_than_min_raises(self):
        with pytest.raises(InvalidTierConfigError):
            PricingTier(min_units=100, max_units=100, unit_price=1.0)


class TestProportionalSplitting:
    def test_price_change_mid_period_splits_evenly(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        mid_point = datetime(2024, 1, 16)
        period_end = datetime(2024, 1, 31)

        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.0),
            effective_from=period_start,
        )
        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.5),
            effective_from=mid_point,
        )

        engine.open_period(period_start, period_end - period_start)
        period = engine.get_current_period()

        engine.report_usage(ACC, RES, 200, reported_at=in_period(period, 5))
        estimates = engine.estimate_current_cost(ACC)
        line = estimates[RES]

        assert len(line.proportional_splits) == 2

        first_split = line.proportional_splits[0]
        second_split = line.proportional_splits[1]

        assert first_split.time_ratio == pytest.approx(0.5, abs=0.02)
        assert first_split.allocated_units == pytest.approx(100, abs=2)
        assert first_split.segment_cost == pytest.approx(100.0, abs=2)

        assert second_split.time_ratio == pytest.approx(0.5, abs=0.02)
        assert second_split.allocated_units == pytest.approx(100, abs=2)
        assert second_split.segment_cost == pytest.approx(150.0, abs=3)

        expected_total = 100.0 + 150.0
        assert line.total_cost == pytest.approx(expected_total, abs=5)

    def test_price_change_at_exact_period_start(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.0),
            effective_from=period_start,
        )

        engine.open_period(period_start, period_end - period_start)
        period = engine.get_current_period()
        engine.report_usage(ACC, RES, 100, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)

        assert len(estimates[RES].proportional_splits) == 1
        assert estimates[RES].total_cost == pytest.approx(100.0)

    def test_price_change_at_exact_period_end(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)

        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.0),
            effective_from=period_start,
        )
        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(999.0),
            effective_from=period_end,
        )

        engine.open_period(period_start, period_end - period_start)
        period = engine.get_current_period()
        engine.report_usage(ACC, RES, 100, reported_at=in_period(period, 1))
        estimates = engine.estimate_current_cost(ACC)

        assert len(estimates[RES].proportional_splits) == 1
        assert estimates[RES].total_cost == pytest.approx(100.0)


class TestPeriodSettlement:
    def test_settle_generates_bill(self):
        engine = build_engine_with_single_tier(RES, 2.0)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 50, reported_at=in_period(period, 1))
        bills = engine.settle_period()

        assert len(bills) == 1
        bill = bills[0]
        assert bill.account_id == ACC
        assert bill.total_amount == pytest.approx(100.0)
        assert len(bill.line_items) == 1
        assert bill.line_items[0].resource_type == RES
        assert bill.line_items[0].total_units == 50

    def test_settle_marks_period_settled(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        assert period.is_active
        engine.settle_period()
        assert period.is_settled
        assert period.status == BillingPeriodStatus.SETTLED

    def test_cannot_report_to_settled_period(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 10, reported_at=in_period(period, 1))
        engine.settle_period()

        with pytest.raises(PeriodSettledError):
            engine.report_usage(ACC, RES, 20, reported_at=in_period(period, 2))

    def test_settle_then_new_period_starts_fresh(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period1 = open_standard_period(engine)

        engine.report_usage(ACC, RES, 100, reported_at=in_period(period1, 1))
        engine.settle_period()
        assert engine.get_current_usage(ACC, RES) == 0

        engine.open_period(datetime(2024, 2, 1), timedelta(days=28))
        period2 = engine.get_current_period()
        assert engine.get_current_usage(ACC, RES) == 0

        engine.report_usage(ACC, RES, 50, reported_at=in_period(period2, 1))
        assert engine.get_current_usage(ACC, RES) == 50

    def test_manual_early_settlement(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 75, reported_at=in_period(period, 1))
        early_end = period.start_time + timedelta(days=10)
        bills = engine.settle_period(end_time=early_end)

        assert len(bills) == 1
        assert period.end_time == early_end
        assert period.is_settled

    def test_cannot_settle_already_settled_period(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)
        engine.settle_period()

        with pytest.raises(PeriodSettledError):
            engine.settle_period(period_id=period.id)

    def test_multiple_accounts_separate_bills(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        engine.report_usage("acc-a", RES, 10, reported_at=in_period(period, 1))
        engine.report_usage("acc-b", RES, 20, reported_at=in_period(period, 2))
        bills = engine.settle_period()

        assert len(bills) == 2
        bill_a = next(b for b in bills if b.account_id == "acc-a")
        bill_b = next(b for b in bills if b.account_id == "acc-b")
        assert bill_a.total_amount == pytest.approx(10.0)
        assert bill_b.total_amount == pytest.approx(20.0)


class TestPeriodBoundary:
    def test_period_switch_at_exact_hour(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        p1_start = datetime(2024, 1, 1, 0, 0, 0)
        p1_end = datetime(2024, 1, 2, 0, 0, 0)

        engine.open_period(p1_start, p1_end - p1_start)
        period1 = engine.get_current_period()
        engine.report_usage(ACC, RES, 10, reported_at=datetime(2024, 1, 1, 23, 59, 59))

        engine.settle_period()

        engine.open_period(p1_end, timedelta(days=1))
        period2 = engine.get_current_period()
        engine.report_usage(ACC, RES, 20, reported_at=datetime(2024, 1, 2, 0, 0, 0))

        assert engine.get_current_usage(ACC, RES) == 20


class TestBillQuery:
    def test_query_bill_history(self):
        engine = build_engine_with_single_tier(RES, 1.0)

        _, period1 = open_standard_period(engine, base_day=1)
        engine.report_usage(ACC, RES, 100, reported_at=in_period(period1, 1))
        engine.settle_period()

        engine.open_period(datetime(2024, 2, 1), timedelta(days=28))
        period2 = engine.get_current_period()
        engine.report_usage(ACC, RES, 50, reported_at=in_period(period2, 1))
        engine.settle_period()

        all_bills = engine.get_bills(ACC)
        assert len(all_bills) == 2

    def test_query_bill_details(self):
        engine = build_engine_with_three_tiers(RES)
        _, period = open_standard_period(engine)

        engine.report_usage(ACC, RES, 600, reported_at=in_period(period, 1))
        bills = engine.settle_period()
        bill = bills[0]

        assert len(bill.line_items) == 1
        line = bill.line_items[0]
        assert line.total_units == 600

        split = line.proportional_splits[0]
        assert len(split.tier_details) == 3

        costs = [d.tier_cost for d in split.tier_details]
        assert sum(costs) == pytest.approx(line.total_cost)


class TestExceptionCases:
    def test_report_usage_for_unknown_resource_raises(self):
        engine = BillingEngine()
        _, period = open_standard_period(engine)

        with pytest.raises(ResourceNotFoundError):
            engine.report_usage(ACC, "no-such-resource", 10, reported_at=in_period(period, 1))

    def test_report_usage_for_resource_pricing_not_effective_yet_raises(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        pricing_effective = datetime(2024, 1, 15)
        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.0),
            effective_from=pricing_effective,
        )
        _, period = open_standard_period(engine, base_day=1)

        with pytest.raises(PricingNotFoundError):
            engine.report_usage(ACC, RES, 10, reported_at=datetime(2024, 1, 5))

    def test_get_bills_for_unknown_account_raises(self):
        engine = BillingEngine()
        from solocoder_py.billing import AccountNotFoundError
        with pytest.raises(AccountNotFoundError):
            engine.get_bills("ghost-account")

    def test_get_bill_for_unknown_account_raises(self):
        engine = BillingEngine()
        from solocoder_py.billing import AccountNotFoundError
        with pytest.raises(AccountNotFoundError):
            engine.get_bill("ghost-account", "fake-bill-id")

    def test_future_usage_timestamp_raises(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        open_standard_period(engine)

        future = datetime.now() + timedelta(days=365)
        with pytest.raises(FutureUsageError):
            engine.report_usage(ACC, RES, 10, reported_at=future)

    def test_no_active_period_raises_on_report(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        with pytest.raises(BillingError):
            engine.report_usage(ACC, RES, 10, reported_at=datetime(2024, 1, 15))

    def test_invalid_period_end_before_start_raises(self):
        from solocoder_py.billing import BillingPeriod
        with pytest.raises(InvalidPeriodError):
            BillingPeriod.create(
                datetime(2024, 1, 2),
                datetime(2024, 1, 1),
            )

    def test_usage_before_period_start_raises(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        open_standard_period(engine)

        too_early = datetime(2023, 12, 15)
        with pytest.raises(InvalidPeriodError):
            engine.report_usage(ACC, RES, 10, reported_at=too_early)

    def test_usage_after_period_end_raises(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        open_standard_period(engine)

        too_late = datetime(2024, 12, 1)
        with pytest.raises(InvalidPeriodError):
            engine.report_usage(ACC, RES, 10, reported_at=too_late)

    def test_cannot_open_period_when_one_active(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        open_standard_period(engine)

        with pytest.raises(BillingError):
            engine.open_period(datetime(2024, 2, 1), timedelta(days=28))

    def test_settle_end_time_before_start_raises(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        with pytest.raises(InvalidPeriodError):
            engine.settle_period(end_time=period.start_time - timedelta(days=1))

    def test_settle_end_time_exceeds_period_end_raises(self):
        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)

        with pytest.raises(InvalidPeriodError):
            engine.settle_period(end_time=period.end_time + timedelta(days=1))


class TestPricingEffectiveTimeBoundary:
    def test_usage_reported_exactly_at_pricing_effective_time_accepted(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        pricing_effective = datetime(2024, 1, 10)
        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.0),
            effective_from=pricing_effective,
        )
        engine.open_period(period_start, timedelta(days=30))

        engine.report_usage(ACC, RES, 10, reported_at=pricing_effective)
        assert engine.get_current_usage(ACC, RES) == 10

    def test_usage_reported_right_after_pricing_effective_accepted(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        pricing_effective = datetime(2024, 1, 10)
        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.0),
            effective_from=pricing_effective,
        )
        engine.open_period(period_start, timedelta(days=30))

        engine.report_usage(ACC, RES, 10, reported_at=pricing_effective + timedelta(seconds=1))
        assert engine.get_current_usage(ACC, RES) == 10

    def test_usage_reported_right_before_pricing_effective_rejected(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        pricing_effective = datetime(2024, 1, 10, 0, 0, 0)
        engine.configure_tiered_pricing(
            RES,
            make_simple_tier(1.0),
            effective_from=pricing_effective,
        )
        engine.open_period(period_start, timedelta(days=30))

        just_before = pricing_effective - timedelta(seconds=1)
        with pytest.raises(PricingNotFoundError):
            engine.report_usage(ACC, RES, 10, reported_at=just_before)

    def test_usage_reported_after_two_price_changes_uses_latest(self):
        engine = BillingEngine()
        period_start = datetime(2024, 1, 1)
        engine.configure_tiered_pricing(
            RES, make_simple_tier(1.0), effective_from=datetime(2024, 1, 1)
        )
        engine.configure_tiered_pricing(
            RES, make_simple_tier(2.0), effective_from=datetime(2024, 1, 15)
        )
        engine.open_period(period_start, timedelta(days=30))
        period = engine.get_current_period()

        engine.report_usage(ACC, RES, 100, reported_at=datetime(2024, 1, 20))
        estimates = engine.estimate_current_cost(ACC)
        line = estimates[RES]
        first_split = line.proportional_splits[0]
        second_split = line.proportional_splits[1]
        assert first_split.tier_details[0].unit_price == 1.0
        assert second_split.tier_details[0].unit_price == 2.0


class TestAmountPrecision:
    def test_bill_amount_rounds_to_two_decimals(self):
        engine = BillingEngine(amount_precision=2)
        _, period = open_standard_period(engine)
        engine.configure_tiered_pricing(
            RES, make_simple_tier(0.3333333), effective_from=period.start_time
        )

        engine.report_usage(ACC, RES, 100, reported_at=in_period(period, 1))
        bills = engine.settle_period()

        assert len(bills) == 1
        assert bills[0].total_amount == pytest.approx(33.33)

    def test_tier_costs_are_rounded(self):
        engine = BillingEngine(amount_precision=2)
        _, period = open_standard_period(engine)
        engine.configure_tiered_pricing(
            RES,
            [
                PricingTier(min_units=0, max_units=100, unit_price=0.123456),
                PricingTier(min_units=100, max_units=None, unit_price=0.654321),
            ],
            effective_from=period.start_time,
        )

        engine.report_usage(ACC, RES, 150, reported_at=in_period(period, 1))
        bills = engine.settle_period()
        line = bills[0].line_items[0]
        split = line.proportional_splits[0]

        first_tier = split.tier_details[0]
        assert first_tier.tier_cost == pytest.approx(12.35)

        second_tier = split.tier_details[1]
        assert second_tier.tier_cost == pytest.approx(32.72)

        assert line.total_cost == pytest.approx(12.35 + 32.72)

    def test_custom_precision(self):
        engine = BillingEngine(amount_precision=4)
        _, period = open_standard_period(engine)
        engine.configure_tiered_pricing(
            RES, make_simple_tier(0.1234567), effective_from=period.start_time
        )

        engine.report_usage(ACC, RES, 1, reported_at=in_period(period, 1))
        bills = engine.settle_period()
        assert bills[0].total_amount == pytest.approx(0.1235)


class TestConcurrency:
    def test_concurrent_report_usage_consistency(self):
        import threading

        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)
        report_time = in_period(period, 1)

        num_threads = 10
        reports_per_thread = 100
        units_per_report = 1.0

        errors: list[Exception] = []

        def worker():
            try:
                for _ in range(reports_per_thread):
                    engine.report_usage(
                        ACC, RES, units_per_report, reported_at=report_time
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        expected = num_threads * reports_per_thread * units_per_report
        assert engine.get_current_usage(ACC, RES) == pytest.approx(expected)

    def test_concurrent_read_write_no_crash(self):
        import threading

        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)
        report_time = in_period(period, 1)

        errors: list[Exception] = []
        stop_flag = threading.Event()

        def writer():
            try:
                for i in range(200):
                    engine.report_usage(
                        ACC, RES, 1.0, reported_at=report_time
                    )
            except Exception as e:
                errors.append(e)
            finally:
                stop_flag.set()

        def reader():
            try:
                while not stop_flag.is_set():
                    _ = engine.get_current_usage(ACC, RES)
                    _ = engine.get_current_period()
                    _ = engine.list_periods()
                    _ = engine.estimate_current_cost(ACC)
                    _ = engine.list_bills()
            except Exception as e:
                errors.append(e)

        t_writer = threading.Thread(target=writer)
        t_reader = threading.Thread(target=reader)
        t_reader.start()
        t_writer.start()
        t_writer.join()
        t_reader.join()

        assert len(errors) == 0

    def test_concurrent_settle_and_report_consistent(self):
        import threading

        engine = build_engine_with_single_tier(RES, 1.0)
        _, period = open_standard_period(engine)
        report_time = in_period(period, 1)

        errors: list[Exception] = []

        for i in range(50):
            engine.report_usage(ACC, RES, 1.0, reported_at=report_time)

        def reporter():
            try:
                for _ in range(50):
                    try:
                        engine.report_usage(
                            ACC, RES, 1.0, reported_at=report_time
                        )
                    except (PeriodSettledError, BillingError):
                        break
            except Exception as e:
                errors.append(e)

        def settler():
            try:
                engine.settle_period()
            except (BillingError, PeriodSettledError):
                pass
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=reporter)
        t2 = threading.Thread(target=settler)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0
