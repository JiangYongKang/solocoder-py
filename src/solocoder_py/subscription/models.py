from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional

from .states import SubscriptionState, SubscriptionStateMachine, InvalidStateTransitionError


class SubscriptionError(Exception):
    pass


class InvalidPlanError(SubscriptionError):
    pass


class InvalidDowngradeError(SubscriptionError):
    pass


class PauseExceededError(SubscriptionError):
    pass


class DuplicateOperationException(SubscriptionError):
    pass


class BillingCycleType(str, Enum):
    MONTHLY = "月付"
    QUARTERLY = "季付"
    YEARLY = "年付"


class OperationType(str, Enum):
    CREATE = "创建订阅"
    ACTIVATE = "激活订阅"
    RENEW = "续费"
    DOWNGRADE_REQUEST = "申请降级"
    DOWNGRADE_APPLY = "降级生效"
    PAUSE = "暂停"
    RESUME = "恢复"
    CANCEL = "取消"
    TERMINATE = "立即终止"
    EXPIRE = "过期"
    AUTO_CANCEL = "暂停超期自动取消"


@dataclass
class SubscriptionPlan:
    name: str
    cycle_type: BillingCycleType
    price: Decimal

    def __post_init__(self) -> None:
        if not self.name:
            raise InvalidPlanError("Plan name cannot be empty")
        if self.price < 0:
            raise InvalidPlanError("Plan price cannot be negative")

    @property
    def cycle_days(self) -> int:
        if self.cycle_type == BillingCycleType.MONTHLY:
            return 30
        elif self.cycle_type == BillingCycleType.QUARTERLY:
            return 90
        else:
            return 365

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SubscriptionPlan):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class SubscriptionOperation:
    id: str
    operation_type: OperationType
    operated_at: datetime
    reason: str = ""
    detail: str = ""


@dataclass
class DowngradeRequest:
    target_plan: SubscriptionPlan
    requested_at: datetime
    effective_at: date


class PlanCatalog:
    def __init__(self) -> None:
        self._plans: Dict[str, SubscriptionPlan] = {}

    def add_plan(self, plan: SubscriptionPlan) -> None:
        if plan.name in self._plans:
            raise InvalidPlanError(f"Plan already exists: {plan.name}")
        self._plans[plan.name] = plan

    def get_plan(self, name: str) -> SubscriptionPlan:
        if name not in self._plans:
            raise InvalidPlanError(f"Plan not found: {name}")
        return self._plans[name]

    def list_plans(self) -> List[SubscriptionPlan]:
        return sorted(self._plans.values(), key=lambda p: p.price)

    def get_cheaper_plans(self, plan: SubscriptionPlan) -> List[SubscriptionPlan]:
        return [
            p for p in self._plans.values()
            if p.price < plan.price and p.cycle_days <= plan.cycle_days
        ]

    def compare_price(self, plan1: SubscriptionPlan, plan2: SubscriptionPlan) -> Decimal:
        return plan1.price - plan2.price


def _calculate_cycle_days(start_date: date, cycle_type: BillingCycleType) -> int:
    if cycle_type == BillingCycleType.MONTHLY:
        next_month = start_date.replace(day=28) + timedelta(days=4)
        next_month_start = next_month.replace(day=1)
        if next_month_start.month == 12:
            month_end = date(next_month_start.year, 12, 31)
        else:
            month_end = date(next_month_start.year, next_month_start.month, 1) - timedelta(days=1)
        return (month_end - start_date).days + 1
    elif cycle_type == BillingCycleType.QUARTERLY:
        quarter_month = ((start_date.month - 1) // 3) * 3 + 1
        if quarter_month + 3 > 12:
            quarter_end = date(start_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            quarter_end = date(start_date.year, quarter_month + 3, 1) - timedelta(days=1)
        return (quarter_end - start_date).days + 1
    else:
        year_end = date(start_date.year, 12, 31)
        return (year_end - start_date).days + 1


def _add_cycle(start_date: date, cycle_type: BillingCycleType) -> date:
    if cycle_type == BillingCycleType.MONTHLY:
        if start_date.month == 12:
            return start_date.replace(year=start_date.year + 1, month=1)
        return start_date.replace(month=start_date.month + 1)
    elif cycle_type == BillingCycleType.QUARTERLY:
        new_month = start_date.month + 3
        if new_month > 12:
            return start_date.replace(year=start_date.year + 1, month=new_month - 12)
        return start_date.replace(month=new_month)
    else:
        return start_date.replace(year=start_date.year + 1)


def calculate_refund(
    cycle_price: Decimal,
    cycle_start: date,
    cycle_end: date,
    as_of: date,
) -> Decimal:
    if as_of >= cycle_end:
        return Decimal("0")
    if as_of <= cycle_start:
        return cycle_price
    total_days = (cycle_end - cycle_start).days
    remaining_days = (cycle_end - as_of).days
    if total_days <= 0:
        return Decimal("0")
    refund = cycle_price * Decimal(remaining_days) / Decimal(total_days)
    return refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class Subscription:
    id: str
    user_id: str
    plan: SubscriptionPlan
    created_at: datetime
    trial_end_at: Optional[date] = None
    current_cycle_start: Optional[date] = None
    current_cycle_end: Optional[date] = None
    _state_machine: SubscriptionStateMachine = field(
        default_factory=lambda: SubscriptionStateMachine(SubscriptionState.TRIAL)
    )
    _operations: List[SubscriptionOperation] = field(default_factory=list)
    _downgrade_request: Optional[DowngradeRequest] = None
    _pause_resume_at: Optional[date] = None
    _pause_end_at: Optional[date] = None
    _cancelled: bool = False

    def __post_init__(self) -> None:
        op = SubscriptionOperation(
            id=str(uuid.uuid4()),
            operation_type=OperationType.CREATE,
            operated_at=self.created_at,
            reason="初始创建",
            detail=f"计划: {self.plan.name}, 周期: {self.plan.cycle_type.value}, 价格: {self.plan.price}",
        )
        self._operations.append(op)

    @property
    def state(self) -> SubscriptionState:
        return self._state_machine.state

    @property
    def plan_name(self) -> str:
        return self.plan.name

    @property
    def next_renewal_date(self) -> Optional[date]:
        if self.state in (SubscriptionState.CANCELLED, SubscriptionState.EXPIRED):
            return None
        return self.current_cycle_end

    @property
    def downgrade_request(self) -> Optional[DowngradeRequest]:
        return self._downgrade_request

    @property
    def operations(self) -> List[SubscriptionOperation]:
        return list(self._operations)

    @property
    def state_history(self) -> List[SubscriptionOperation]:
        state_ops = [
            OperationType.CREATE,
            OperationType.ACTIVATE,
            OperationType.PAUSE,
            OperationType.RESUME,
            OperationType.DOWNGRADE_REQUEST,
            OperationType.DOWNGRADE_APPLY,
            OperationType.CANCEL,
            OperationType.TERMINATE,
            OperationType.EXPIRE,
            OperationType.AUTO_CANCEL,
        ]
        return [op for op in self._operations if op.operation_type in state_ops]

    def _add_operation(
        self,
        op_type: OperationType,
        now: datetime,
        reason: str = "",
        detail: str = "",
    ) -> None:
        op = SubscriptionOperation(
            id=str(uuid.uuid4()),
            operation_type=op_type,
            operated_at=now,
            reason=reason,
            detail=detail,
        )
        self._operations.append(op)

    def activate(self, now: Optional[datetime] = None, reason: str = "试用期结束自动激活") -> None:
        now = now or datetime.now()
        if self.state != SubscriptionState.TRIAL:
            raise InvalidStateTransitionError(self.state, SubscriptionState.ACTIVE)
        self._state_machine.transition_to(SubscriptionState.ACTIVE)
        start_date = now.date()
        self.current_cycle_start = start_date
        self.current_cycle_end = _add_cycle(start_date, self.plan.cycle_type)
        self._add_operation(
            OperationType.ACTIVATE,
            now,
            reason=reason,
            detail=f"周期: {self.current_cycle_start} ~ {self.current_cycle_end}",
        )

    def renew(self, now: Optional[datetime] = None, reason: str = "用户续费") -> None:
        now = now or datetime.now()
        if self.state not in (SubscriptionState.ACTIVE, SubscriptionState.DOWNGRADE_PENDING):
            raise InvalidStateTransitionError(self.state, SubscriptionState.ACTIVE)

        if self._downgrade_request is not None:
            target_plan = self._downgrade_request.target_plan
            self.plan = target_plan
            self._downgrade_request = None
            self._add_operation(
                OperationType.DOWNGRADE_APPLY,
                now,
                reason="续费时降级生效",
                detail=f"新计划: {self.plan.name}",
            )

        new_start = self.current_cycle_end if self.current_cycle_end else now.date()
        self.current_cycle_start = new_start
        self.current_cycle_end = _add_cycle(new_start, self.plan.cycle_type)
        self._state_machine.set_state(SubscriptionState.ACTIVE)
        self._add_operation(
            OperationType.RENEW,
            now,
            reason=reason,
            detail=f"新周期: {self.current_cycle_start} ~ {self.current_cycle_end}, 计划: {self.plan.name}",
        )

    def downgrade(
        self,
        target_plan: SubscriptionPlan,
        now: Optional[datetime] = None,
        reason: str = "用户申请降级",
    ) -> None:
        now = now or datetime.now()
        if self.state not in (SubscriptionState.ACTIVE, SubscriptionState.DOWNGRADE_PENDING):
            raise InvalidStateTransitionError(self.state, SubscriptionState.DOWNGRADE_PENDING)

        if target_plan.price >= self.plan.price:
            raise InvalidDowngradeError(
                f"Cannot downgrade to plan with higher or equal price: "
                f"{self.plan.price} -> {target_plan.price}"
            )
        if target_plan.cycle_days > self.plan.cycle_days:
            raise InvalidDowngradeError(
                f"Cannot downgrade to plan with longer cycle: "
                f"{self.plan.cycle_type.value} -> {target_plan.cycle_type.value}"
            )

        self._downgrade_request = DowngradeRequest(
            target_plan=target_plan,
            requested_at=now,
            effective_at=self.current_cycle_end if self.current_cycle_end else now.date(),
        )
        if self.state == SubscriptionState.ACTIVE:
            self._state_machine.transition_to(SubscriptionState.DOWNGRADE_PENDING)
        self._add_operation(
            OperationType.DOWNGRADE_REQUEST,
            now,
            reason=reason,
            detail=f"降级到: {target_plan.name}, 生效日期: {self._downgrade_request.effective_at}",
        )

    def pause(
        self,
        pause_days: int,
        now: Optional[datetime] = None,
        reason: str = "用户申请暂停",
    ) -> None:
        now = now or datetime.now()
        if self.state not in (SubscriptionState.ACTIVE, SubscriptionState.DOWNGRADE_PENDING):
            raise InvalidStateTransitionError(self.state, SubscriptionState.PAUSED)

        if pause_days <= 0:
            raise PauseExceededError("Pause days must be positive")

        if self.current_cycle_end is not None:
            max_pause_days = (self.current_cycle_end - now.date()).days
            if pause_days > max_pause_days + 1:
                raise PauseExceededError(
                    f"Pause days ({pause_days}) exceeds remaining cycle days ({max_pause_days + 1})"
                )

        self._pause_resume_at = now.date() + timedelta(days=pause_days)
        self._pause_end_at = self.current_cycle_end
        if self.current_cycle_end is not None:
            self.current_cycle_end = self.current_cycle_end + timedelta(days=pause_days)
        self._state_machine.transition_to(SubscriptionState.PAUSED)
        self._add_operation(
            OperationType.PAUSE,
            now,
            reason=reason,
            detail=f"暂停天数: {pause_days}, 预计恢复: {self._pause_resume_at}, 新周期结束: {self.current_cycle_end}",
        )

    def resume(self, now: Optional[datetime] = None, reason: str = "用户恢复订阅") -> None:
        now = now or datetime.now()
        if self.state != SubscriptionState.PAUSED:
            raise InvalidStateTransitionError(self.state, SubscriptionState.ACTIVE)
        self._pause_resume_at = None
        self._pause_end_at = None
        if self._downgrade_request is not None:
            self._state_machine.transition_to(SubscriptionState.DOWNGRADE_PENDING)
        else:
            self._state_machine.transition_to(SubscriptionState.ACTIVE)
        self._add_operation(
            OperationType.RESUME,
            now,
            reason=reason,
        )

    def cancel(self, now: Optional[datetime] = None, reason: str = "用户取消订阅") -> None:
        now = now or datetime.now()
        if self._cancelled:
            raise DuplicateOperationException("Subscription already cancelled")
        if self.state in (SubscriptionState.CANCELLED, SubscriptionState.EXPIRED):
            raise DuplicateOperationException(f"Cannot cancel subscription in state: {self.state.value}")

        self._state_machine.transition_to(SubscriptionState.CANCELLED)
        self._cancelled = True
        self._add_operation(
            OperationType.CANCEL,
            now,
            reason=reason,
            detail=f"到期日期: {self.current_cycle_end}",
        )

    def terminate(
        self,
        now: Optional[datetime] = None,
        reason: str = "立即终止",
    ) -> Decimal:
        now = now or datetime.now()
        if self.state == SubscriptionState.EXPIRED:
            raise DuplicateOperationException("Subscription already expired")

        refund_amount = Decimal("0")
        if self.state in (SubscriptionState.ACTIVE, SubscriptionState.DOWNGRADE_PENDING, SubscriptionState.PAUSED):
            if self.current_cycle_start and self.current_cycle_end:
                refund_amount = calculate_refund(
                    self.plan.price,
                    self.current_cycle_start,
                    self.current_cycle_end,
                    now.date(),
                )

        self._state_machine.set_state(SubscriptionState.EXPIRED)
        self._add_operation(
            OperationType.TERMINATE,
            now,
            reason=reason,
            detail=f"退款金额: {refund_amount}",
        )
        return refund_amount

    def check_expiry(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.now()
        today = now.date()

        if self.state == SubscriptionState.TRIAL and self.trial_end_at and today >= self.trial_end_at:
            self.activate(now=now, reason="试用期结束自动激活")
            return

        if self.state == SubscriptionState.PAUSED:
            if self._pause_resume_at and today >= self._pause_resume_at:
                if self._pause_end_at and self._pause_end_at <= today:
                    self._state_machine.set_state(SubscriptionState.EXPIRED)
                    self._add_operation(
                        OperationType.AUTO_CANCEL,
                        now,
                        reason="暂停超期自动取消",
                    )
                    return
                self.resume(now=now, reason="暂停到期自动恢复")
                return

        if self.current_cycle_end and today >= self.current_cycle_end:
            if self.state == SubscriptionState.CANCELLED:
                self._state_machine.transition_to(SubscriptionState.EXPIRED)
                self._add_operation(
                    OperationType.EXPIRE,
                    now,
                    reason="取消后到期自动过期",
                )
            elif self.state in (SubscriptionState.ACTIVE, SubscriptionState.DOWNGRADE_PENDING):
                pass

    def preview_refund(self, as_of: Optional[date] = None) -> Decimal:
        as_of = as_of or date.today()
        if not self.current_cycle_start or not self.current_cycle_end:
            return Decimal("0")
        if self.state in (SubscriptionState.TRIAL, SubscriptionState.EXPIRED):
            return Decimal("0")
        return calculate_refund(
            self.plan.price,
            self.current_cycle_start,
            self.current_cycle_end,
            as_of,
        )
