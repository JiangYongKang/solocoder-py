from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from .states import RefundState, RefundStateMachine
from .exceptions import (
    ExcessRefundError,
    InvalidRefundAmountError,
    ChargebackAmountError,
)


@dataclass
class Payment:
    id: str
    user_id: str
    amount: Decimal
    currency: str = "CNY"
    created_at: datetime = field(default_factory=datetime.now)
    refunded_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    charged_back_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    refund_ids: List[str] = field(default_factory=list)
    chargeback_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Payment amount must be positive")
        if self.refunded_amount < 0:
            raise ValueError("refunded_amount cannot be negative")
        if self.charged_back_amount < 0:
            raise ValueError("charged_back_amount cannot be negative")

    @property
    def available_refund_amount(self) -> Decimal:
        return self.amount - self.refunded_amount

    @property
    def is_fully_refunded(self) -> bool:
        return self.available_refund_amount <= 0

    def can_refund(self, amount: Decimal) -> bool:
        if amount <= 0:
            return False
        return amount <= self.available_refund_amount

    def add_refunded_amount(self, amount: Decimal) -> None:
        if amount <= 0:
            raise InvalidRefundAmountError("Refund amount must be positive")
        if not self.can_refund(amount):
            raise ExcessRefundError(
                requested=float(amount),
                available=float(self.available_refund_amount),
            )
        self.refunded_amount += amount

    def rollback_refunded_amount(self, amount: Decimal) -> None:
        if amount <= 0:
            raise InvalidRefundAmountError("Rollback amount must be positive")
        if amount > self.refunded_amount:
            raise ChargebackAmountError(
                f"Rollback amount {amount} exceeds refunded amount {self.refunded_amount}"
            )
        self.refunded_amount -= amount
        self.charged_back_amount += amount


@dataclass
class Chargeback:
    id: str
    payment_id: str
    refund_id: Optional[str]
    amount: Decimal
    reason: str
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Chargeback amount must be positive")


@dataclass
class Refund:
    id: str
    payment_id: str
    amount: Decimal
    reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    chargeback_id: Optional[str] = None
    _state_machine: RefundStateMachine = field(
        default_factory=lambda: RefundStateMachine(RefundState.REFUND_REQUESTED)
    )

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise InvalidRefundAmountError("Refund amount must be positive")

    @property
    def state(self) -> RefundState:
        return self._state_machine.state

    @property
    def can_be_reviewed(self) -> bool:
        return self.state == RefundState.REFUND_REQUESTED

    @property
    def can_be_approved(self) -> bool:
        return self.state == RefundState.UNDER_REVIEW

    @property
    def can_be_rejected(self) -> bool:
        return self.state == RefundState.UNDER_REVIEW

    @property
    def can_be_cancelled(self) -> bool:
        return self.state == RefundState.REFUND_REQUESTED

    @property
    def can_be_charged_back(self) -> bool:
        return self.state in (RefundState.UNDER_REVIEW, RefundState.REFUNDED)

    def start_review(self) -> None:
        self._state_machine.transition_to(RefundState.UNDER_REVIEW)
        self.reviewed_at = datetime.now()

    def approve(self) -> None:
        self._state_machine.transition_to(RefundState.REFUNDED)
        self.completed_at = datetime.now()

    def reject(self) -> None:
        self._state_machine.transition_to(RefundState.REJECTED)
        self.completed_at = datetime.now()

    def cancel(self) -> None:
        self._state_machine.transition_to(RefundState.CANCELLED)
        self.completed_at = datetime.now()

    def apply_chargeback(self, chargeback_id: str) -> None:
        self._state_machine.transition_to(RefundState.CHARGED_BACK)
        self.chargeback_id = chargeback_id
        self.completed_at = datetime.now()


def make_payment(user_id: str, amount: Decimal, currency: str = "CNY") -> Payment:
    return Payment(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,
        currency=currency,
    )


def make_refund(
    payment_id: str, amount: Decimal, reason: str = ""
) -> Refund:
    return Refund(
        id=str(uuid.uuid4()),
        payment_id=payment_id,
        amount=amount,
        reason=reason,
    )


def make_chargeback(
    payment_id: str,
    refund_id: Optional[str],
    amount: Decimal,
    reason: str,
) -> Chargeback:
    return Chargeback(
        id=str(uuid.uuid4()),
        payment_id=payment_id,
        refund_id=refund_id,
        amount=amount,
        reason=reason,
    )
