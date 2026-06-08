from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from solocoder_py.subscription import (
    BillingCycleType,
    InvalidDowngradeError,
    InvalidStateTransitionError,
    DuplicateOperationException,
    PauseExceededError,
    Subscription,
    SubscriptionPlan,
    SubscriptionState,
    OperationType,
    calculate_refund,
)
from tests.subscription.conftest import (
    make_basic_monthly_plan,
    make_pro_monthly_plan,
    make_pro_quarterly_plan,
    make_pro_yearly_plan,
    make_enterprise_monthly_plan,
    make_subscription,
    make_active_subscription,
)


class TestBoundaryConditions:
    def test_trial_period_exactly_ends(self):
        created_at = datetime(2024, 1, 1, 10, 0, 0)
        sub = make_subscription(created_at=created_at, trial_days=7)
        assert sub.trial_end_at == date(2024, 1, 8)

        exact_end_time = datetime(2024, 1, 8, 0, 0, 0)
        sub.check_expiry(now=exact_end_time)
        assert sub.state == SubscriptionState.ACTIVE

    def test_trial_period_one_day_before_end(self):
        created_at = datetime(2024, 1, 1, 10, 0, 0)
        sub = make_subscription(created_at=created_at, trial_days=7)

        before_end = datetime(2024, 1, 7, 23, 59, 59)
        sub.check_expiry(now=before_end)
        assert sub.state == SubscriptionState.TRIAL

    def test_downgrade_on_last_day_of_cycle(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        last_day = datetime(2024, 1, 31, 23, 59, 59)
        sub.downgrade(basic_plan, now=last_day)

        assert sub.state == SubscriptionState.DOWNGRADE_PENDING
        assert sub.downgrade_request.effective_at == sub.current_cycle_end

        renew_time = datetime(2024, 2, 1, 0, 0, 0)
        sub.renew(now=renew_time)
        assert sub.state == SubscriptionState.ACTIVE
        assert sub.plan.name == "basic-monthly"

    def test_refund_remaining_days_zero(self):
        sub = make_active_subscription()
        cycle_end = sub.current_cycle_end
        refund = sub.preview_refund(as_of=cycle_end)
        assert refund == Decimal("0")

    def test_refund_full_refund_at_start(self):
        sub = make_active_subscription()
        cycle_start = sub.current_cycle_start
        refund = sub.preview_refund(as_of=cycle_start)
        assert refund == sub.plan.price

    def test_refund_leap_year_february_monthly(self):
        plan = SubscriptionPlan(
            name="leap-test",
            cycle_type=BillingCycleType.MONTHLY,
            price=Decimal("290.00"),
        )
        activated_at = datetime(2024, 2, 1, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 2, 1)
        assert sub.current_cycle_end == date(2024, 3, 1)

        mid_feb = date(2024, 2, 15)
        refund = sub.preview_refund(as_of=mid_feb)
        total_days = 29
        remaining_days = 15
        expected = (Decimal("290.00") * Decimal(remaining_days) / Decimal(total_days)).quantize(Decimal("0.01"))
        assert refund == expected

    def test_refund_non_leap_year_february(self):
        plan = SubscriptionPlan(
            name="non-leap-test",
            cycle_type=BillingCycleType.MONTHLY,
            price=Decimal("280.00"),
        )
        activated_at = datetime(2023, 2, 1, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)

        mid_feb = date(2023, 2, 15)
        refund = sub.preview_refund(as_of=mid_feb)
        total_days = 28
        remaining_days = 14
        expected = (Decimal("280.00") * Decimal(remaining_days) / Decimal(total_days)).quantize(Decimal("0.01"))
        assert refund == expected

    def test_pause_max_remaining_days(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 25, 10, 0, 0)
        remaining_days = (sub.current_cycle_end - pause_time.date()).days + 1
        sub.pause(pause_days=remaining_days, now=pause_time)
        assert sub.state == SubscriptionState.PAUSED

    def test_cancelled_subscription_expires_exactly_on_end_date(self):
        sub = make_active_subscription()
        cancel_time = datetime(2024, 1, 15, 10, 0, 0)
        sub.cancel(now=cancel_time)
        assert sub.state == SubscriptionState.CANCELLED

        exact_expire = datetime(2024, 2, 1, 0, 0, 0)
        sub.check_expiry(now=exact_expire)
        assert sub.state == SubscriptionState.EXPIRED

    def test_yearly_plan_december_renewal(self):
        plan = make_pro_yearly_plan()
        activated_at = datetime(2024, 12, 15, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 12, 15)
        assert sub.current_cycle_end == date(2025, 12, 15)

    def test_quarterly_plan_q4_renewal(self):
        plan = make_pro_quarterly_plan()
        activated_at = datetime(2024, 11, 1, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 11, 1)
        assert sub.current_cycle_end == date(2025, 2, 1)


class TestErrorCases:
    def test_activate_from_non_trial_state(self):
        sub = make_active_subscription()
        with pytest.raises(InvalidStateTransitionError) as exc:
            sub.activate()
        assert exc.value.current == SubscriptionState.ACTIVE
        assert exc.value.target == SubscriptionState.ACTIVE

    def test_renew_from_trial_state(self):
        sub = make_subscription(trial_days=7)
        with pytest.raises(InvalidStateTransitionError):
            sub.renew()

    def test_renew_from_cancelled_state(self):
        sub = make_active_subscription()
        sub.cancel()
        with pytest.raises(InvalidStateTransitionError):
            sub.renew()

    def test_renew_from_paused_state(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 5, 10, 0, 0)
        sub.pause(pause_days=5, now=pause_time)
        with pytest.raises(InvalidStateTransitionError):
            sub.renew()

    def test_downgrade_from_trial_state(self):
        sub = make_subscription()
        basic_plan = make_basic_monthly_plan()
        with pytest.raises(InvalidStateTransitionError):
            sub.downgrade(basic_plan)

    def test_downgrade_from_paused_state(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 5, 10, 0, 0)
        sub.pause(pause_days=5, now=pause_time)
        basic_plan = make_basic_monthly_plan()
        with pytest.raises(InvalidStateTransitionError):
            sub.downgrade(basic_plan)

    def test_downgrade_to_higher_price_rejected(self):
        sub = make_active_subscription()
        enterprise = make_enterprise_monthly_plan()
        with pytest.raises(InvalidDowngradeError) as exc:
            sub.downgrade(enterprise)
        assert "higher or equal price" in str(exc.value)

    def test_downgrade_to_equal_price_rejected(self):
        sub = make_active_subscription()
        same_price_plan = SubscriptionPlan(
            name="same-price",
            cycle_type=BillingCycleType.MONTHLY,
            price=Decimal("199.00"),
        )
        with pytest.raises(InvalidDowngradeError):
            sub.downgrade(same_price_plan)

    def test_downgrade_to_longer_cycle_rejected(self):
        sub = make_active_subscription()
        longer_cycle_cheaper = SubscriptionPlan(
            name="longer-cycle",
            cycle_type=BillingCycleType.YEARLY,
            price=Decimal("99.00"),
        )
        with pytest.raises(InvalidDowngradeError) as exc:
            sub.downgrade(longer_cycle_cheaper)
        assert "longer cycle" in str(exc.value)

    def test_pause_from_trial_state(self):
        sub = make_subscription()
        with pytest.raises(InvalidStateTransitionError):
            sub.pause(pause_days=5)

    def test_pause_from_cancelled_state(self):
        sub = make_active_subscription()
        sub.cancel()
        with pytest.raises(InvalidStateTransitionError):
            sub.pause(pause_days=5)

    def test_pause_zero_days_raises_error(self):
        sub = make_active_subscription()
        with pytest.raises(PauseExceededError):
            sub.pause(pause_days=0)

    def test_pause_negative_days_raises_error(self):
        sub = make_active_subscription()
        with pytest.raises(PauseExceededError):
            sub.pause(pause_days=-1)

    def test_pause_exceeds_remaining_cycle_days(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 25, 10, 0, 0)
        remaining_days = (sub.current_cycle_end - pause_time.date()).days + 1
        with pytest.raises(PauseExceededError):
            sub.pause(pause_days=remaining_days + 1, now=pause_time)

    def test_resume_from_non_paused_state(self):
        sub = make_active_subscription()
        with pytest.raises(InvalidStateTransitionError):
            sub.resume()

    def test_cancel_already_cancelled_subscription(self):
        sub = make_active_subscription()
        sub.cancel()
        with pytest.raises(DuplicateOperationException):
            sub.cancel()

    def test_cancel_expired_subscription(self):
        sub = make_active_subscription()
        sub.terminate()
        with pytest.raises(DuplicateOperationException):
            sub.cancel()

    def test_terminate_already_expired_subscription(self):
        sub = make_active_subscription()
        sub.terminate()
        with pytest.raises(DuplicateOperationException):
            sub.terminate()

    def test_pause_auto_cancel_when_pause_exceeds_cycle(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 28, 10, 0, 0)
        sub.pause(pause_days=4, now=pause_time)

        check_time = datetime(2024, 2, 2, 10, 0, 0)
        sub.check_expiry(now=check_time)
        assert sub.state == SubscriptionState.EXPIRED

        auto_cancel_ops = [
            op for op in sub.operations
            if op.operation_type == OperationType.AUTO_CANCEL
        ]
        assert len(auto_cancel_ops) == 1

    def test_operations_on_expired_subscription_all_rejected(self):
        sub = make_active_subscription()
        sub.terminate()
        basic_plan = make_basic_monthly_plan()

        with pytest.raises(InvalidStateTransitionError):
            sub.activate()
        with pytest.raises(InvalidStateTransitionError):
            sub.renew()
        with pytest.raises(InvalidStateTransitionError):
            sub.downgrade(basic_plan)
        with pytest.raises(InvalidStateTransitionError):
            sub.pause(pause_days=5)
        with pytest.raises(InvalidStateTransitionError):
            sub.resume()
        with pytest.raises(DuplicateOperationException):
            sub.cancel()
        with pytest.raises(DuplicateOperationException):
            sub.terminate()
