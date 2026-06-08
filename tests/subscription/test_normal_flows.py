from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from solocoder_py.subscription import (
    BillingCycleType,
    Subscription,
    SubscriptionState,
    OperationType,
    calculate_refund,
)
from tests.subscription.conftest import (
    make_basic_monthly_plan,
    make_pro_monthly_plan,
    make_pro_quarterly_plan,
    make_pro_yearly_plan,
    make_subscription,
    make_active_subscription,
)


class TestTrialToActiveRenewFlow:
    def test_create_subscription_trial_state(self):
        sub = make_subscription(trial_days=7)
        assert sub.state == SubscriptionState.TRIAL
        assert sub.plan_name == "pro-monthly"
        assert sub.trial_end_at == date(2024, 1, 8)

    def test_manual_activate_from_trial(self):
        sub = make_subscription(trial_days=7)
        activate_time = datetime(2024, 1, 3, 10, 0, 0)
        sub.activate(now=activate_time, reason="用户提前激活")
        assert sub.state == SubscriptionState.ACTIVE
        assert sub.current_cycle_start == date(2024, 1, 3)
        assert sub.current_cycle_end == date(2024, 2, 3)
        assert sub.next_renewal_date == date(2024, 2, 3)

    def test_trial_auto_activate_on_expiry(self):
        sub = make_subscription(trial_days=7)
        check_time = datetime(2024, 1, 8, 10, 0, 0)
        sub.check_expiry(now=check_time)
        assert sub.state == SubscriptionState.ACTIVE

    def test_renew_active_subscription(self):
        sub = make_active_subscription()
        assert sub.state == SubscriptionState.ACTIVE
        assert sub.current_cycle_start == date(2024, 1, 1)
        assert sub.current_cycle_end == date(2024, 2, 1)

        renew_time = datetime(2024, 2, 1, 10, 0, 0)
        sub.renew(now=renew_time)
        assert sub.state == SubscriptionState.ACTIVE
        assert sub.current_cycle_start == date(2024, 2, 1)
        assert sub.current_cycle_end == date(2024, 3, 1)

    def test_renew_quarterly_subscription(self):
        plan = make_pro_quarterly_plan()
        sub = make_active_subscription(plan=plan)
        assert sub.current_cycle_start == date(2024, 1, 1)
        assert sub.current_cycle_end == date(2024, 4, 1)

        renew_time = datetime(2024, 4, 1, 10, 0, 0)
        sub.renew(now=renew_time)
        assert sub.current_cycle_start == date(2024, 4, 1)
        assert sub.current_cycle_end == date(2024, 7, 1)

    def test_renew_yearly_subscription(self):
        plan = make_pro_yearly_plan()
        sub = make_active_subscription(plan=plan)
        assert sub.current_cycle_start == date(2024, 1, 1)
        assert sub.current_cycle_end == date(2025, 1, 1)

    def test_create_operation_recorded(self):
        sub = make_subscription()
        ops = sub.operations
        assert len(ops) >= 1
        assert ops[0].operation_type == OperationType.CREATE
        assert ops[0].reason == "初始创建"

    def test_activate_operation_recorded(self):
        sub = make_subscription()
        activate_time = datetime(2024, 1, 5, 10, 0, 0)
        sub.activate(now=activate_time, reason="手动激活")
        ops = sub.operations
        activate_op = [op for op in ops if op.operation_type == OperationType.ACTIVATE][0]
        assert activate_op.operated_at == activate_time
        assert activate_op.reason == "手动激活"

    def test_state_history_includes_relevant_ops(self):
        sub = make_active_subscription()
        renew_time = datetime(2024, 2, 1, 10, 0, 0)
        sub.renew(now=renew_time)
        history = sub.state_history
        op_types = [op.operation_type for op in history]
        assert OperationType.CREATE in op_types
        assert OperationType.ACTIVATE in op_types
        assert OperationType.RENEW in op_types


class TestEndOfMonthDateHandling:
    def test_monthly_jan_31_to_feb_non_leap_year(self):
        plan = make_pro_monthly_plan()
        activated_at = datetime(2023, 1, 31, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2023, 1, 31)
        assert sub.current_cycle_end == date(2023, 2, 28)

    def test_monthly_jan_31_to_feb_leap_year(self):
        plan = make_pro_monthly_plan()
        activated_at = datetime(2024, 1, 31, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 1, 31)
        assert sub.current_cycle_end == date(2024, 2, 29)

    def test_monthly_mar_31_to_april(self):
        plan = make_pro_monthly_plan()
        activated_at = datetime(2024, 3, 31, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 3, 31)
        assert sub.current_cycle_end == date(2024, 4, 30)

    def test_monthly_dec_31_to_jan(self):
        plan = make_pro_monthly_plan()
        activated_at = datetime(2024, 12, 31, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 12, 31)
        assert sub.current_cycle_end == date(2025, 1, 31)

    def test_quarterly_jan_31_to_april(self):
        plan = make_pro_quarterly_plan()
        activated_at = datetime(2024, 1, 31, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 1, 31)
        assert sub.current_cycle_end == date(2024, 4, 30)

    def test_quarterly_nov_30_to_feb(self):
        plan = make_pro_quarterly_plan()
        activated_at = datetime(2024, 11, 30, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 11, 30)
        assert sub.current_cycle_end == date(2025, 2, 28)

    def test_yearly_leap_day_feb_29(self):
        plan = make_pro_yearly_plan()
        activated_at = datetime(2024, 2, 29, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_start == date(2024, 2, 29)
        assert sub.current_cycle_end == date(2025, 2, 28)

    def test_renew_from_leap_year_feb_29_preserves_day_29(self):
        plan = make_pro_monthly_plan()
        activated_at = datetime(2024, 1, 31, 10, 0, 0)
        sub = make_active_subscription(plan=plan, activated_at=activated_at)
        assert sub.current_cycle_end == date(2024, 2, 29)

        renew_time = datetime(2024, 2, 29, 10, 0, 0)
        sub.renew(now=renew_time)
        assert sub.current_cycle_start == date(2024, 2, 29)
        assert sub.current_cycle_end == date(2024, 3, 29)


class TestAutoDowngradeOnExpiry:
    def test_downgrade_pending_auto_applies_on_cycle_end(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        downgrade_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.downgrade(basic_plan, now=downgrade_time)
        assert sub.state == SubscriptionState.DOWNGRADE_PENDING
        assert sub.plan.name == "pro-monthly"

        check_time = datetime(2024, 2, 1, 10, 0, 0)
        sub.check_expiry(now=check_time)

        assert sub.state == SubscriptionState.ACTIVE
        assert sub.plan.name == "basic-monthly"
        assert sub.downgrade_request is None
        assert sub.current_cycle_start == date(2024, 2, 1)
        assert sub.current_cycle_end == date(2024, 3, 1)

    def test_auto_downgrade_records_operation(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        downgrade_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.downgrade(basic_plan, now=downgrade_time)

        check_time = datetime(2024, 2, 1, 10, 0, 0)
        sub.check_expiry(now=check_time)

        apply_ops = [
            op for op in sub.operations
            if op.operation_type == OperationType.DOWNGRADE_APPLY
        ]
        assert len(apply_ops) == 1
        assert apply_ops[0].reason == "到期自动降级生效"
        assert "basic-monthly" in apply_ops[0].detail

    def test_no_auto_downgrade_before_cycle_end(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        downgrade_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.downgrade(basic_plan, now=downgrade_time)

        check_time = datetime(2024, 1, 31, 10, 0, 0)
        sub.check_expiry(now=check_time)

        assert sub.state == SubscriptionState.DOWNGRADE_PENDING
        assert sub.plan.name == "pro-monthly"
        assert sub.downgrade_request is not None


class TestDowngradeFlow:
    def test_request_downgrade_from_active(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        downgrade_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.downgrade(basic_plan, now=downgrade_time, reason="用户降级")

        assert sub.state == SubscriptionState.DOWNGRADE_PENDING
        assert sub.downgrade_request is not None
        assert sub.downgrade_request.target_plan == basic_plan
        assert sub.downgrade_request.effective_at == sub.current_cycle_end
        assert sub.plan.name == "pro-monthly"

    def test_downgrade_applied_on_renew(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        downgrade_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.downgrade(basic_plan, now=downgrade_time)

        renew_time = datetime(2024, 2, 1, 10, 0, 0)
        sub.renew(now=renew_time)

        assert sub.state == SubscriptionState.ACTIVE
        assert sub.plan.name == "basic-monthly"
        assert sub.downgrade_request is None
        assert sub.current_cycle_start == date(2024, 2, 1)
        assert sub.current_cycle_end == date(2024, 3, 1)

    def test_pause_while_downgrade_pending(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        downgrade_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.downgrade(basic_plan, now=downgrade_time)
        assert sub.state == SubscriptionState.DOWNGRADE_PENDING

        pause_time = datetime(2024, 1, 12, 10, 0, 0)
        sub.pause(pause_days=5, now=pause_time)
        assert sub.state == SubscriptionState.PAUSED

    def test_resume_returns_to_downgrade_pending(self):
        sub = make_active_subscription()
        basic_plan = make_basic_monthly_plan()
        downgrade_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.downgrade(basic_plan, now=downgrade_time)

        pause_time = datetime(2024, 1, 12, 10, 0, 0)
        sub.pause(pause_days=5, now=pause_time)

        resume_time = datetime(2024, 1, 17, 10, 0, 0)
        sub.resume(now=resume_time)
        assert sub.state == SubscriptionState.DOWNGRADE_PENDING


class TestPauseResumeFlow:
    def test_pause_active_subscription(self):
        sub = make_active_subscription()
        original_end = sub.current_cycle_end
        pause_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.pause(pause_days=7, now=pause_time, reason="用户申请暂停")

        assert sub.state == SubscriptionState.PAUSED
        assert sub.current_cycle_end == original_end + timedelta(days=7)

    def test_resume_paused_subscription(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.pause(pause_days=7, now=pause_time)

        resume_time = datetime(2024, 1, 17, 10, 0, 0)
        sub.resume(now=resume_time, reason="用户恢复")
        assert sub.state == SubscriptionState.ACTIVE

    def test_auto_resume_on_pause_expiry(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.pause(pause_days=7, now=pause_time)
        assert sub.state == SubscriptionState.PAUSED

        check_time = datetime(2024, 1, 17, 10, 0, 0)
        sub.check_expiry(now=check_time)
        assert sub.state == SubscriptionState.ACTIVE

    def test_pause_operation_recorded(self):
        sub = make_active_subscription()
        pause_time = datetime(2024, 1, 10, 10, 0, 0)
        sub.pause(pause_days=7, now=pause_time, reason="测试暂停")

        pause_ops = [op for op in sub.operations if op.operation_type == OperationType.PAUSE]
        assert len(pause_ops) == 1
        assert pause_ops[0].reason == "测试暂停"
        assert "暂停天数: 7" in pause_ops[0].detail


class TestCancelAndTerminateFlow:
    def test_cancel_active_subscription(self):
        sub = make_active_subscription()
        cancel_time = datetime(2024, 1, 15, 10, 0, 0)
        sub.cancel(now=cancel_time, reason="用户取消")
        assert sub.state == SubscriptionState.CANCELLED
        assert sub.next_renewal_date is None

    def test_cancelled_auto_expire(self):
        sub = make_active_subscription()
        cancel_time = datetime(2024, 1, 15, 10, 0, 0)
        sub.cancel(now=cancel_time)
        assert sub.state == SubscriptionState.CANCELLED

        expire_time = datetime(2024, 2, 1, 10, 0, 0)
        sub.check_expiry(now=expire_time)
        assert sub.state == SubscriptionState.EXPIRED

    def test_terminate_with_refund(self):
        sub = make_active_subscription()
        terminate_time = datetime(2024, 1, 16, 10, 0, 0)
        refund = sub.terminate(now=terminate_time, reason="管理员终止")

        assert sub.state == SubscriptionState.EXPIRED
        assert refund > Decimal("0")
        assert refund <= sub.plan.price

    def test_terminate_operation_includes_refund(self):
        sub = make_active_subscription()
        terminate_time = datetime(2024, 1, 16, 10, 0, 0)
        sub.terminate(now=terminate_time)

        terminate_ops = [op for op in sub.operations if op.operation_type == OperationType.TERMINATE]
        assert len(terminate_ops) == 1
        assert "退款金额:" in terminate_ops[0].detail


class TestRefundCalculation:
    def test_refund_mid_cycle(self):
        price = Decimal("31.00")
        cycle_start = date(2024, 1, 1)
        cycle_end = date(2024, 2, 1)
        as_of = date(2024, 1, 16)

        refund = calculate_refund(price, cycle_start, cycle_end, as_of)
        assert refund == Decimal("16.00")

    def test_refund_at_cycle_start(self):
        price = Decimal("100.00")
        cycle_start = date(2024, 1, 1)
        cycle_end = date(2024, 2, 1)
        as_of = date(2024, 1, 1)

        refund = calculate_refund(price, cycle_start, cycle_end, as_of)
        assert refund == price

    def test_refund_before_cycle_start(self):
        price = Decimal("100.00")
        cycle_start = date(2024, 1, 1)
        cycle_end = date(2024, 2, 1)
        as_of = date(2023, 12, 15)

        refund = calculate_refund(price, cycle_start, cycle_end, as_of)
        assert refund == price

    def test_refund_at_cycle_end(self):
        price = Decimal("100.00")
        cycle_start = date(2024, 1, 1)
        cycle_end = date(2024, 2, 1)
        as_of = date(2024, 2, 1)

        refund = calculate_refund(price, cycle_start, cycle_end, as_of)
        assert refund == Decimal("0")

    def test_refund_after_cycle_end(self):
        price = Decimal("100.00")
        cycle_start = date(2024, 1, 1)
        cycle_end = date(2024, 2, 1)
        as_of = date(2024, 2, 15)

        refund = calculate_refund(price, cycle_start, cycle_end, as_of)
        assert refund == Decimal("0")

    def test_refund_leap_year_february(self):
        price = Decimal("29.00")
        cycle_start = date(2024, 2, 1)
        cycle_end = date(2024, 3, 1)
        as_of = date(2024, 2, 15)

        refund = calculate_refund(price, cycle_start, cycle_end, as_of)
        total_days = 29
        remaining_days = 15
        expected = (price * Decimal(remaining_days) / Decimal(total_days)).quantize(Decimal("0.01"))
        assert refund == expected

    def test_refund_quarterly(self):
        plan = make_pro_quarterly_plan()
        sub = make_active_subscription(plan=plan)
        preview_time = date(2024, 1, 16)
        refund = sub.preview_refund(as_of=preview_time)
        assert refund > Decimal("0")
        assert refund < plan.price

    def test_preview_refund_in_trial_state(self):
        sub = make_subscription(trial_days=7)
        refund = sub.preview_refund()
        assert refund == Decimal("0")

    def test_preview_refund_in_expired_state(self):
        sub = make_active_subscription()
        sub.terminate()
        refund = sub.preview_refund()
        assert refund == Decimal("0")
