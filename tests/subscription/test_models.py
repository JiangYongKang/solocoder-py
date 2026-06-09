from datetime import datetime, date
from decimal import Decimal

import pytest

from solocoder_py.subscription import (
    BillingCycleType,
    InvalidPlanError,
    InvalidDowngradeError,
    PlanCatalog,
    SubscriptionPlan,
    OperationType,
)
from tests.subscription.conftest import (
    make_basic_monthly_plan,
    make_pro_monthly_plan,
    make_pro_quarterly_plan,
    make_pro_yearly_plan,
    make_default_catalog,
)


class TestSubscriptionPlan:
    def test_plan_creation(self):
        plan = SubscriptionPlan(
            name="test-plan",
            cycle_type=BillingCycleType.MONTHLY,
            price=Decimal("99.00"),
        )
        assert plan.name == "test-plan"
        assert plan.cycle_type == BillingCycleType.MONTHLY
        assert plan.price == Decimal("99.00")

    def test_plan_cycle_days(self):
        monthly = make_basic_monthly_plan()
        quarterly = make_pro_quarterly_plan()
        yearly = make_pro_yearly_plan()
        assert monthly.cycle_days == 30
        assert quarterly.cycle_days == 90
        assert yearly.cycle_days == 365

    def test_empty_plan_name_raises_error(self):
        with pytest.raises(InvalidPlanError) as exc:
            SubscriptionPlan(
                name="",
                cycle_type=BillingCycleType.MONTHLY,
                price=Decimal("99.00"),
            )
        assert "Plan name cannot be empty" in str(exc.value)

    def test_negative_plan_price_raises_error(self):
        with pytest.raises(InvalidPlanError) as exc:
            SubscriptionPlan(
                name="test",
                cycle_type=BillingCycleType.MONTHLY,
                price=Decimal("-1.00"),
            )
        assert "Plan price cannot be negative" in str(exc.value)

    def test_plan_equality(self):
        plan1 = make_basic_monthly_plan()
        plan2 = make_basic_monthly_plan()
        plan3 = make_pro_monthly_plan()
        assert plan1 == plan2
        assert plan1 != plan3
        assert plan1 != "not-a-plan"

    def test_plan_hash(self):
        plan1 = make_basic_monthly_plan()
        plan2 = make_basic_monthly_plan()
        assert hash(plan1) == hash(plan2)


class TestPlanCatalog:
    def test_add_and_get_plan(self):
        catalog = PlanCatalog()
        plan = make_basic_monthly_plan()
        catalog.add_plan(plan)
        assert catalog.get_plan("basic-monthly") == plan

    def test_add_duplicate_plan_raises_error(self):
        catalog = make_default_catalog()
        plan = make_basic_monthly_plan()
        with pytest.raises(InvalidPlanError):
            catalog.add_plan(plan)

    def test_get_nonexistent_plan_raises_error(self):
        catalog = PlanCatalog()
        with pytest.raises(InvalidPlanError):
            catalog.get_plan("nonexistent")

    def test_list_plans_sorted_by_price(self):
        catalog = make_default_catalog()
        plans = catalog.list_plans()
        assert len(plans) == 5
        for i in range(len(plans) - 1):
            assert plans[i].price <= plans[i + 1].price

    def test_get_cheaper_plans(self):
        catalog = make_default_catalog()
        pro_monthly = make_pro_monthly_plan()
        cheaper = catalog.get_cheaper_plans(pro_monthly)
        assert len(cheaper) == 1
        assert cheaper[0].name == "basic-monthly"

    def test_get_cheaper_plans_excludes_longer_cycle(self):
        catalog = make_default_catalog()
        pro_yearly = make_pro_yearly_plan()
        cheaper = catalog.get_cheaper_plans(pro_yearly)
        for plan in cheaper:
            assert plan.price < pro_yearly.price
            assert plan.cycle_days <= pro_yearly.cycle_days

    def test_compare_price(self):
        catalog = PlanCatalog()
        basic = make_basic_monthly_plan()
        pro = make_pro_monthly_plan()
        assert catalog.compare_price(pro, basic) == Decimal("100.00")
        assert catalog.compare_price(basic, pro) == Decimal("-100.00")


class TestOperationType:
    def test_operation_type_values(self):
        assert OperationType.CREATE.value == "创建订阅"
        assert OperationType.ACTIVATE.value == "激活订阅"
        assert OperationType.RENEW.value == "续费"
        assert OperationType.DOWNGRADE_REQUEST.value == "申请降级"
        assert OperationType.DOWNGRADE_APPLY.value == "降级生效"
        assert OperationType.PAUSE.value == "暂停"
        assert OperationType.RESUME.value == "恢复"
        assert OperationType.CANCEL.value == "取消"
        assert OperationType.TERMINATE.value == "立即终止"
        assert OperationType.EXPIRE.value == "过期"
        assert OperationType.AUTO_CANCEL.value == "暂停超期自动取消"
