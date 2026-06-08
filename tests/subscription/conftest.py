from datetime import datetime, timedelta, date
from decimal import Decimal
import uuid
from typing import Optional

from solocoder_py.subscription import (
    Subscription,
    SubscriptionPlan,
    BillingCycleType,
    SubscriptionState,
    PlanCatalog,
    OperationType,
)


def make_basic_monthly_plan() -> SubscriptionPlan:
    return SubscriptionPlan(
        name="basic-monthly",
        cycle_type=BillingCycleType.MONTHLY,
        price=Decimal("99.00"),
    )


def make_pro_monthly_plan() -> SubscriptionPlan:
    return SubscriptionPlan(
        name="pro-monthly",
        cycle_type=BillingCycleType.MONTHLY,
        price=Decimal("199.00"),
    )


def make_pro_quarterly_plan() -> SubscriptionPlan:
    return SubscriptionPlan(
        name="pro-quarterly",
        cycle_type=BillingCycleType.QUARTERLY,
        price=Decimal("499.00"),
    )


def make_pro_yearly_plan() -> SubscriptionPlan:
    return SubscriptionPlan(
        name="pro-yearly",
        cycle_type=BillingCycleType.YEARLY,
        price=Decimal("1899.00"),
    )


def make_enterprise_monthly_plan() -> SubscriptionPlan:
    return SubscriptionPlan(
        name="enterprise-monthly",
        cycle_type=BillingCycleType.MONTHLY,
        price=Decimal("499.00"),
    )


def make_default_catalog() -> PlanCatalog:
    catalog = PlanCatalog()
    catalog.add_plan(make_basic_monthly_plan())
    catalog.add_plan(make_pro_monthly_plan())
    catalog.add_plan(make_pro_quarterly_plan())
    catalog.add_plan(make_pro_yearly_plan())
    catalog.add_plan(make_enterprise_monthly_plan())
    return catalog


def make_subscription(
    plan: Optional[SubscriptionPlan] = None,
    trial_days: int = 7,
    created_at: Optional[datetime] = None,
    user_id: str = "user-001",
) -> Subscription:
    if plan is None:
        plan = make_pro_monthly_plan()
    if created_at is None:
        created_at = datetime(2024, 1, 1, 10, 0, 0)
    trial_end_at = created_at.date() + timedelta(days=trial_days) if trial_days > 0 else None
    return Subscription(
        id=str(uuid.uuid4()),
        user_id=user_id,
        plan=plan,
        created_at=created_at,
        trial_end_at=trial_end_at,
    )


def make_active_subscription(
    plan: Optional[SubscriptionPlan] = None,
    activated_at: Optional[datetime] = None,
) -> Subscription:
    sub = make_subscription(plan=plan, trial_days=0)
    if activated_at is None:
        activated_at = datetime(2024, 1, 1, 10, 0, 0)
    sub.activate(now=activated_at, reason="手动激活")
    return sub


def advance_subscription_to_active(
    sub: Subscription,
    activate_time: Optional[datetime] = None,
) -> None:
    if activate_time is None:
        activate_time = datetime(2024, 1, 1, 10, 0, 0)
    sub.activate(now=activate_time, reason="手动激活")
