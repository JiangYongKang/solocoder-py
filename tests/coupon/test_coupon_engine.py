from datetime import timedelta

import pytest

from solocoder_py.coupon import (
    CouponEngine,
    CouponMutexError,
    CouponType,
    DuplicateCouponError,
    InvalidCouponError,
    Tier,
    TierDiscountType,
)

from .conftest import (
    base_time,
    make_engine,
    make_expired_fixed_coupon,
    make_fixed_coupon,
    make_future_fixed_coupon,
    make_percentage_coupon,
    make_tiered_coupon,
)


class TestCouponModelValidation:
    def test_fixed_amount_invalid_threshold(self):
        with pytest.raises(InvalidCouponError):
            make_fixed_coupon("c1", threshold=-1, discount_amount=10)

    def test_fixed_amount_invalid_discount(self):
        with pytest.raises(InvalidCouponError):
            make_fixed_coupon("c1", threshold=100, discount_amount=0)

    def test_percentage_invalid_rate_zero(self):
        with pytest.raises(InvalidCouponError):
            make_percentage_coupon("c1", threshold=100, discount_rate=0)

    def test_percentage_invalid_rate_over_one(self):
        with pytest.raises(InvalidCouponError):
            make_percentage_coupon("c1", threshold=100, discount_rate=1.5)

    def test_invalid_validity_range(self):
        from .conftest import valid_range
        vf, vu = valid_range()
        with pytest.raises(InvalidCouponError):
            from solocoder_py.coupon import FixedAmountCoupon
            FixedAmountCoupon(
                coupon_id="c1",
                name="bad",
                valid_from=vu,
                valid_until=vf,
                threshold=100,
                discount_amount=10,
            )

    def test_invalid_max_discount_negative(self):
        with pytest.raises(InvalidCouponError):
            make_fixed_coupon("c1", 100, 10, max_discount=-5)

    def test_tiered_empty_tiers(self):
        with pytest.raises(InvalidCouponError):
            make_tiered_coupon("c1", tiers=[])

    def test_tiered_overlapping_tiers(self):
        tiers = [
            Tier(0, 100, TierDiscountType.FIXED_AMOUNT, 10),
            Tier(50, 200, TierDiscountType.FIXED_AMOUNT, 20),
        ]
        with pytest.raises(InvalidCouponError):
            make_tiered_coupon("c1", tiers=tiers)

    def test_tiered_percentage_over_one(self):
        with pytest.raises(InvalidCouponError):
            Tier(0, None, TierDiscountType.PERCENTAGE, 1.5)

    def test_tiered_negative_min(self):
        with pytest.raises(InvalidCouponError):
            Tier(-10, 100, TierDiscountType.FIXED_AMOUNT, 10)


class TestSingleCouponFixedAmount:
    def test_above_threshold(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", threshold=100, discount_amount=20)
        result = engine.calculate(200.0, [coupon])
        assert result.original_amount == 200.0
        assert result.final_amount == 180.0
        assert result.total_discount == 20.0
        assert len(result.details) == 1
        d = result.details[0]
        assert d.applied is True
        assert d.discount_amount == 20.0
        assert d.amount_before == 200.0
        assert d.amount_after == 180.0
        assert d.coupon_type == CouponType.FIXED_AMOUNT

    def test_exactly_at_threshold(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", threshold=100, discount_amount=20)
        result = engine.calculate(100.0, [coupon])
        assert result.final_amount == 80.0
        assert result.total_discount == 20.0
        assert result.details[0].applied is True
        assert result.details[0].excluded_by_threshold is False

    def test_below_threshold(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", threshold=100, discount_amount=20)
        result = engine.calculate(50.0, [coupon])
        assert result.final_amount == 50.0
        assert result.total_discount == 0.0
        d = result.details[0]
        assert d.applied is False
        assert d.excluded_by_threshold is True

    def test_with_max_discount_cap(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", threshold=100, discount_amount=50, max_discount=30)
        result = engine.calculate(200.0, [coupon])
        assert result.total_discount == 30.0
        assert result.final_amount == 170.0
        assert result.details[0].capped is True

    def test_discount_equals_cap(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", threshold=100, discount_amount=30, max_discount=30)
        result = engine.calculate(200.0, [coupon])
        assert result.total_discount == 30.0
        assert result.details[0].capped is True

    def test_discount_exceeds_order_amount(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", threshold=5, discount_amount=100)
        result = engine.calculate(10.0, [coupon])
        assert result.final_amount == 0.0
        assert result.total_discount == 10.0


class TestSingleCouponPercentage:
    def test_above_threshold(self):
        engine = make_engine()
        coupon = make_percentage_coupon("c1", threshold=100, discount_rate=0.2)
        result = engine.calculate(200.0, [coupon])
        assert result.total_discount == 40.0
        assert result.final_amount == 160.0
        assert result.details[0].coupon_type == CouponType.PERCENTAGE

    def test_exactly_at_threshold(self):
        engine = make_engine()
        coupon = make_percentage_coupon("c1", threshold=100, discount_rate=0.1)
        result = engine.calculate(100.0, [coupon])
        assert result.total_discount == 10.0
        assert result.final_amount == 90.0

    def test_below_threshold(self):
        engine = make_engine()
        coupon = make_percentage_coupon("c1", threshold=100, discount_rate=0.2)
        result = engine.calculate(50.0, [coupon])
        assert result.total_discount == 0.0
        assert result.details[0].excluded_by_threshold is True

    def test_with_max_discount_cap(self):
        engine = make_engine()
        coupon = make_percentage_coupon("c1", threshold=0, discount_rate=0.5, max_discount=30)
        result = engine.calculate(100.0, [coupon])
        assert result.total_discount == 30.0
        assert result.details[0].capped is True


class TestSingleCouponTiered:
    def test_tiered_fixed_amount_tiers(self):
        tiers = [
            Tier(0, 100, TierDiscountType.FIXED_AMOUNT, 5),
            Tier(100, 300, TierDiscountType.FIXED_AMOUNT, 20),
            Tier(300, None, TierDiscountType.FIXED_AMOUNT, 50),
        ]
        engine = make_engine()
        coupon = make_tiered_coupon("c1", tiers=tiers)

        r1 = engine.calculate(50.0, [coupon])
        assert r1.total_discount == 5.0

        r2 = engine.calculate(100.0, [coupon])
        assert r2.total_discount == 20.0

        r3 = engine.calculate(200.0, [coupon])
        assert r3.total_discount == 20.0

        r4 = engine.calculate(300.0, [coupon])
        assert r4.total_discount == 50.0

        r5 = engine.calculate(500.0, [coupon])
        assert r5.total_discount == 50.0

    def test_tiered_percentage_tiers(self):
        tiers = [
            Tier(0, 100, TierDiscountType.PERCENTAGE, 0.05),
            Tier(100, 300, TierDiscountType.PERCENTAGE, 0.10),
            Tier(300, None, TierDiscountType.PERCENTAGE, 0.15),
        ]
        engine = make_engine()
        coupon = make_tiered_coupon("c1", tiers=tiers)

        assert engine.calculate(50.0, [coupon]).total_discount == pytest.approx(2.5)
        assert engine.calculate(200.0, [coupon]).total_discount == pytest.approx(20.0)
        assert engine.calculate(400.0, [coupon]).total_discount == pytest.approx(60.0)

    def test_tiered_with_max_discount_cap(self):
        tiers = [
            Tier(0, None, TierDiscountType.PERCENTAGE, 0.5),
        ]
        engine = make_engine()
        coupon = make_tiered_coupon("c1", tiers=tiers, max_discount=30)
        result = engine.calculate(100.0, [coupon])
        assert result.total_discount == 30.0
        assert result.details[0].capped is True


class TestCouponMutualExclusion:
    def test_two_fixed_amount_default_mutex_raises(self):
        engine = make_engine()
        c1 = make_fixed_coupon("c1", 100, 10)
        c2 = make_fixed_coupon("c2", 100, 20)
        with pytest.raises(CouponMutexError):
            engine.calculate(200.0, [c1, c2])

    def test_fixed_and_percentage_default_mutex_raises(self):
        engine = make_engine()
        c1 = make_fixed_coupon("c1", 100, 10)
        c2 = make_percentage_coupon("c2", 100, 0.1)
        with pytest.raises(CouponMutexError):
            engine.calculate(200.0, [c1, c2])

    def test_two_percentage_default_mutex_raises(self):
        engine = make_engine()
        c1 = make_percentage_coupon("c1", 100, 0.1)
        c2 = make_percentage_coupon("c2", 100, 0.2)
        with pytest.raises(CouponMutexError):
            engine.calculate(200.0, [c1, c2])

    def test_tiered_and_fixed_can_stack(self):
        tiers = [Tier(0, None, TierDiscountType.FIXED_AMOUNT, 15)]
        engine = make_engine()
        c_tiered = make_tiered_coupon("c1", tiers=tiers)
        c_fixed = make_fixed_coupon("c2", 0, 10, mutex_groups=["other"])
        result = engine.calculate(100.0, [c_tiered, c_fixed])
        assert result.total_discount == 25.0
        assert result.final_amount == 75.0

    def test_tiered_and_percentage_can_stack(self):
        tiers = [Tier(0, None, TierDiscountType.FIXED_AMOUNT, 15)]
        engine = make_engine()
        c_tiered = make_tiered_coupon("c1", tiers=tiers)
        c_pct = make_percentage_coupon("c2", 0, 0.1, mutex_groups=["other"])
        result = engine.calculate(100.0, [c_tiered, c_pct])
        assert result.final_amount == 76.5

    def test_custom_mutex_groups_conflict(self):
        engine = make_engine()
        c1 = make_fixed_coupon("c1", 0, 10, mutex_groups=["group-a", "group-b"])
        c2 = make_fixed_coupon("c2", 0, 20, mutex_groups=["group-x", "group-b"])
        with pytest.raises(CouponMutexError) as exc_info:
            engine.calculate(100.0, [c1, c2])
        assert exc_info.value.group == "group-b"

    def test_custom_mutex_groups_no_conflict(self):
        engine = make_engine()
        c1 = make_fixed_coupon("c1", 0, 10, mutex_groups=["group-a"])
        c2 = make_fixed_coupon("c2", 0, 20, mutex_groups=["group-b"])
        result = engine.calculate(100.0, [c1, c2])
        assert result.total_discount == 30.0


class TestAutoResolveMutex:
    def test_auto_resolve_higher_priority_wins(self):
        engine = make_engine(auto_resolve_mutex=True)
        c_low = make_fixed_coupon("c-low", 0, 10, priority=1)
        c_high = make_fixed_coupon("c-high", 0, 30, priority=10)
        result = engine.calculate(100.0, [c_low, c_high])
        assert result.total_discount == 30.0
        low_detail = next(d for d in result.details if d.coupon_id == "c-low")
        high_detail = next(d for d in result.details if d.coupon_id == "c-high")
        assert low_detail.excluded_by_mutex is True
        assert low_detail.applied is False
        assert high_detail.applied is True

    def test_auto_resolve_same_priority_id_order(self):
        engine = make_engine(auto_resolve_mutex=True)
        c_a = make_fixed_coupon("c-a", 0, 10, priority=5)
        c_b = make_fixed_coupon("c-b", 0, 30, priority=5)
        result = engine.calculate(100.0, [c_b, c_a])
        applied = [d for d in result.details if d.applied]
        excluded = [d for d in result.details if d.excluded_by_mutex]
        assert len(applied) == 1
        assert applied[0].coupon_id == "c-a"
        assert excluded[0].coupon_id == "c-b"


class TestCouponStackingOrder:
    def test_stacking_order_by_priority(self):
        engine = make_engine()
        c_first = make_percentage_coupon("c-first", 0, 0.1, priority=10, mutex_groups=["g1"])
        c_second = make_fixed_coupon("c-second", 0, 10, priority=1, mutex_groups=["g2"])
        result = engine.calculate(200.0, [c_second, c_first])
        details_by_id = {d.coupon_id: d for d in result.details}
        assert details_by_id["c-first"].amount_before == 200.0
        assert details_by_id["c-first"].amount_after == 180.0
        assert details_by_id["c-second"].amount_before == 180.0
        assert details_by_id["c-second"].amount_after == 170.0
        assert result.final_amount == 170.0

    def test_stacking_three_coupons(self):
        engine = make_engine()
        c1 = make_fixed_coupon("c1", 0, 50, priority=3, mutex_groups=["g1"])
        c2 = make_percentage_coupon("c2", 0, 0.2, priority=2, mutex_groups=["g2"])
        c3 = make_fixed_coupon("c3", 0, 10, priority=1, mutex_groups=["g3"])
        result = engine.calculate(300.0, [c3, c1, c2])
        assert result.original_amount == 300.0
        assert result.final_amount == 190.0
        assert result.total_discount == 110.0


class TestGlobalDiscountCap:
    def test_global_cap_applied(self):
        engine = make_engine(global_max_discount=30)
        c1 = make_fixed_coupon("c1", 0, 20, mutex_groups=["g1"])
        c2 = make_fixed_coupon("c2", 0, 20, mutex_groups=["g2"])
        result = engine.calculate(100.0, [c1, c2])
        assert result.global_capped is True
        assert result.total_discount == 30.0
        assert result.final_amount == 70.0

    def test_global_cap_not_exceeded(self):
        engine = make_engine(global_max_discount=100)
        c1 = make_fixed_coupon("c1", 0, 20, mutex_groups=["g1"])
        c2 = make_fixed_coupon("c2", 0, 20, mutex_groups=["g2"])
        result = engine.calculate(100.0, [c1, c2])
        assert result.global_capped is False
        assert result.total_discount == 40.0

    def test_global_cap_exactly_reached(self):
        engine = make_engine(global_max_discount=40)
        c1 = make_fixed_coupon("c1", 0, 20, mutex_groups=["g1"])
        c2 = make_fixed_coupon("c2", 0, 20, mutex_groups=["g2"])
        result = engine.calculate(100.0, [c1, c2])
        assert result.global_capped is True
        assert result.total_discount == 40.0


class TestCouponValidity:
    def test_expired_coupon_excluded(self):
        engine = make_engine()
        coupon = make_expired_fixed_coupon("c-expired", 0, 50)
        result = engine.calculate(100.0, [coupon])
        assert result.total_discount == 0.0
        d = result.details[0]
        assert d.excluded_by_expiry is True
        assert d.applied is False
        assert "expired" in d.exclusion_reason.lower() or "not yet" in d.exclusion_reason.lower()

    def test_future_coupon_excluded(self):
        engine = make_engine()
        coupon = make_future_fixed_coupon("c-future", 0, 50)
        result = engine.calculate(100.0, [coupon])
        assert result.details[0].excluded_by_expiry is True

    def test_expired_and_valid_mixed(self):
        engine = make_engine()
        c_expired = make_expired_fixed_coupon("c-exp", 0, 30)
        c_valid = make_fixed_coupon("c-valid", 0, 20, mutex_groups=["other"])
        result = engine.calculate(100.0, [c_expired, c_valid])
        assert result.total_discount == 20.0
        exp_detail = next(d for d in result.details if d.coupon_id == "c-exp")
        valid_detail = next(d for d in result.details if d.coupon_id == "c-valid")
        assert exp_detail.excluded_by_expiry is True
        assert valid_detail.applied is True


class TestDuplicateAndEdgeCases:
    def test_duplicate_coupon_id_raises(self):
        engine = make_engine()
        c1 = make_fixed_coupon("dup", 0, 10, mutex_groups=["g1"])
        c2 = make_fixed_coupon("dup", 0, 20, mutex_groups=["g2"])
        with pytest.raises(DuplicateCouponError):
            engine.calculate(100.0, [c1, c2])

    def test_zero_order_amount(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", 0, 50)
        result = engine.calculate(0.0, [coupon])
        assert result.final_amount == 0.0
        assert result.total_discount == 0.0

    def test_negative_order_amount_raises(self):
        engine = make_engine()
        coupon = make_fixed_coupon("c1", 0, 50)
        with pytest.raises(InvalidCouponError):
            engine.calculate(-10.0, [coupon])

    def test_no_coupons(self):
        engine = make_engine()
        result = engine.calculate(100.0, [])
        assert result.original_amount == 100.0
        assert result.final_amount == 100.0
        assert result.total_discount == 0.0
        assert len(result.details) == 0

    def test_stacking_does_not_go_negative(self):
        engine = make_engine()
        c1 = make_fixed_coupon("c1", 0, 60, mutex_groups=["g1"])
        c2 = make_fixed_coupon("c2", 0, 60, mutex_groups=["g2"])
        result = engine.calculate(100.0, [c1, c2])
        assert result.final_amount == 0.0
        assert result.total_discount == 100.0

    def test_check_time_override(self):
        from solocoder_py.coupon import FixedAmountCoupon
        t = base_time()
        coupon = FixedAmountCoupon(
            coupon_id="c1",
            name="test",
            valid_from=t - timedelta(days=1),
            valid_until=t + timedelta(days=1),
            threshold=0,
            discount_amount=10,
        )
        engine_valid = CouponEngine(check_time=t)
        result = engine_valid.calculate(100.0, [coupon])
        assert result.details[0].excluded_by_expiry is False

        engine_expired = CouponEngine(check_time=t + timedelta(days=10))
        result2 = engine_expired.calculate(100.0, [coupon])
        assert result2.details[0].excluded_by_expiry is True


class TestDetailAccuracy:
    def test_detail_fields_populated_correctly(self):
        engine = make_engine()
        c1 = make_fixed_coupon("c1", 100, 20, priority=2, mutex_groups=["g1"])
        c2 = make_percentage_coupon("c2", 0, 0.1, priority=1, mutex_groups=["g2"])
        result = engine.calculate(200.0, [c2, c1])
        assert len(result.details) == 2
        for d in result.details:
            assert d.coupon_id in ("c1", "c2")
            assert d.coupon_name
            assert d.excluded_by_mutex is False
            assert d.excluded_by_expiry is False
            assert d.excluded_by_threshold is False
            assert d.applied is True
            assert d.discount_amount > 0
            assert d.amount_after == d.amount_before - d.discount_amount
            assert d.capped is False

    def test_global_cap_reflected_in_details(self):
        engine = make_engine(global_max_discount=15)
        c1 = make_fixed_coupon("c1", 0, 10, priority=2, mutex_groups=["g1"])
        c2 = make_fixed_coupon("c2", 0, 10, priority=1, mutex_groups=["g2"])
        result = engine.calculate(100.0, [c1, c2])
        assert result.global_capped is True
        capped_details = [d for d in result.details if d.capped]
        assert len(capped_details) == 1
        assert capped_details[0].coupon_id == "c2"
        assert capped_details[0].discount_amount == 5.0


class TestTieredCouponContiguity:
    def test_tiers_with_gap_raises(self):
        tiers = [
            Tier(0, 50, TierDiscountType.FIXED_AMOUNT, 5),
            Tier(100, 200, TierDiscountType.FIXED_AMOUNT, 20),
        ]
        with pytest.raises(InvalidCouponError, match="contiguous"):
            make_tiered_coupon("c1", tiers=tiers)

    def test_tiers_with_large_gap_raises(self):
        tiers = [
            Tier(0, 100, TierDiscountType.PERCENTAGE, 0.05),
            Tier(500, None, TierDiscountType.PERCENTAGE, 0.15),
        ]
        with pytest.raises(InvalidCouponError, match="contiguous"):
            make_tiered_coupon("c1", tiers=tiers)

    def test_tiers_contiguous_accepted(self):
        tiers = [
            Tier(0, 100, TierDiscountType.FIXED_AMOUNT, 5),
            Tier(100, 300, TierDiscountType.FIXED_AMOUNT, 20),
            Tier(300, None, TierDiscountType.FIXED_AMOUNT, 50),
        ]
        coupon = make_tiered_coupon("c1", tiers=tiers)
        assert len(coupon.tiers) == 3

    def test_tiers_overlap_raises(self):
        tiers = [
            Tier(0, 100, TierDiscountType.FIXED_AMOUNT, 5),
            Tier(50, 200, TierDiscountType.FIXED_AMOUNT, 20),
        ]
        with pytest.raises(InvalidCouponError, match="contiguous"):
            make_tiered_coupon("c1", tiers=tiers)


class TestGlobalCapRollbackChainConsistency:
    def test_multi_coupon_rollback_chain_consistent(self):
        engine = make_engine(global_max_discount=25)
        c1 = make_fixed_coupon("c1", 0, 15, priority=3, mutex_groups=["g1"])
        c2 = make_fixed_coupon("c2", 0, 10, priority=2, mutex_groups=["g2"])
        c3 = make_fixed_coupon("c3", 0, 10, priority=1, mutex_groups=["g3"])
        result = engine.calculate(100.0, [c3, c1, c2])

        assert result.total_discount == 25.0
        assert result.final_amount == 75.0
        assert result.global_capped is True

        applied = [d for d in result.details if d.applied]
        applied.sort(key=lambda d: (-d.amount_before, d.coupon_id))
        assert len(applied) == 3

        prev_after = result.original_amount
        for d in applied:
            assert d.amount_before == pytest.approx(prev_after)
            assert d.amount_after == pytest.approx(d.amount_before - d.discount_amount)
            prev_after = d.amount_after
        assert prev_after == pytest.approx(result.final_amount)

    def test_five_coupons_rollback_chain_consistent(self):
        engine = make_engine(global_max_discount=30)
        coupons = []
        for i in range(5):
            coupons.append(make_fixed_coupon(
                f"c{i}", 0, 10, priority=5 - i, mutex_groups=[f"g{i}"]
            ))
        result = engine.calculate(200.0, coupons)

        assert result.global_capped is True
        assert result.total_discount == 30.0

        applied = [d for d in result.details if d.applied]
        applied.sort(key=lambda d: -d.amount_before)

        prev = result.original_amount
        for d in applied:
            assert d.amount_before == pytest.approx(prev)
            assert d.amount_after == pytest.approx(d.amount_before - d.discount_amount)
            prev = d.amount_after
        assert prev == pytest.approx(result.final_amount)

    def test_rollback_sum_matches_total_discount(self):
        engine = make_engine(global_max_discount=22)
        c1 = make_percentage_coupon("c1", 0, 0.2, priority=2, mutex_groups=["g1"])
        c2 = make_fixed_coupon("c2", 0, 15, priority=1, mutex_groups=["g2"])
        result = engine.calculate(100.0, [c1, c2])

        assert result.global_capped is True
        applied_discounts = sum(d.discount_amount for d in result.details if d.applied)
        assert applied_discounts == pytest.approx(result.total_discount)
        assert applied_discounts == pytest.approx(22.0)


class TestInputImmutability:
    def test_calculate_does_not_mutate_input_coupons(self):
        coupon = make_fixed_coupon("c1", threshold=100, discount_amount=20)
        original_mutex_groups = list(coupon.mutex_groups)
        original_name = coupon.name

        engine = make_engine()
        engine.calculate(200.0, [coupon])

        assert coupon.mutex_groups == original_mutex_groups
        assert coupon.name == original_name

    def test_calculate_does_not_mutate_multiple_inputs(self):
        tiers = [Tier(0, None, TierDiscountType.FIXED_AMOUNT, 5)]
        c1 = make_fixed_coupon("c1", 0, 10, mutex_groups=[])
        c2 = make_tiered_coupon("c2", tiers=tiers, mutex_groups=[])
        c1_groups_before = list(c1.mutex_groups)
        c2_groups_before = list(c2.mutex_groups)
        assert len(c1_groups_before) == 0
        assert len(c2_groups_before) == 0

        engine = make_engine()
        engine.calculate(100.0, [c1, c2])

        assert c1.mutex_groups == c1_groups_before
        assert c2.mutex_groups == c2_groups_before
        assert len(c1.mutex_groups) == 0
        assert len(c2.mutex_groups) == 0

    def test_custom_mutex_groups_preserved(self):
        c1 = make_fixed_coupon("c1", 0, 10, mutex_groups=["custom-group"])
        c2 = make_fixed_coupon("c2", 0, 10, mutex_groups=["custom-group"])
        groups_before_1 = list(c1.mutex_groups)
        groups_before_2 = list(c2.mutex_groups)

        engine = make_engine(auto_resolve_mutex=True)
        engine.calculate(100.0, [c1, c2])

        assert c1.mutex_groups == groups_before_1
        assert c2.mutex_groups == groups_before_2
