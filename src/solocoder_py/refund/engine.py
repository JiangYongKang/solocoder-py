from __future__ import annotations

from decimal import Decimal
from typing import Optional

from .models import (
    Payment,
    Refund,
    Chargeback,
    make_payment,
    make_refund,
    make_chargeback,
)
from .repository import RefundRepository
from .states import RefundState
from .exceptions import (
    ExcessRefundError,
    InvalidRefundAmountError,
    RefundStateError,
    RefundOwnershipError,
    ChargebackAmountError,
)


class RefundEngine:
    def __init__(self, repository: Optional[RefundRepository] = None) -> None:
        self._repo = repository or RefundRepository()

    @property
    def repository(self) -> RefundRepository:
        return self._repo

    def create_payment(
        self, user_id: str, amount: Decimal, currency: str = "CNY"
    ) -> Payment:
        payment = make_payment(user_id=user_id, amount=amount, currency=currency)
        self._repo.save_payment(payment)
        return payment

    def request_refund(
        self, payment_id: str, amount: Decimal, reason: str = ""
    ) -> Refund:
        if amount <= 0:
            raise InvalidRefundAmountError("Refund amount must be positive")

        payment = self._repo.get_payment(payment_id)

        if not payment.can_refund(amount):
            raise ExcessRefundError(
                requested=float(amount),
                available=float(payment.available_refund_amount),
            )

        refund = make_refund(payment_id=payment_id, amount=amount, reason=reason)
        self._repo.save_refund(refund)
        payment.refund_ids.append(refund.id)
        return refund

    def start_review(self, refund_id: str) -> Refund:
        refund = self._repo.get_refund(refund_id)
        if not refund.can_be_reviewed:
            raise RefundStateError(
                f"Cannot start review for refund in state: {refund.state.value}"
            )
        refund.start_review()
        return refund

    def approve_refund(self, refund_id: str) -> Refund:
        refund = self._repo.get_refund(refund_id)
        if not refund.can_be_approved:
            raise RefundStateError(
                f"Cannot approve refund in state: {refund.state.value}"
            )

        payment = self._repo.get_payment(refund.payment_id)
        payment.add_refunded_amount(refund.amount)

        refund.approve()
        return refund

    def reject_refund(self, refund_id: str) -> Refund:
        refund = self._repo.get_refund(refund_id)
        if not refund.can_be_rejected:
            raise RefundStateError(
                f"Cannot reject refund in state: {refund.state.value}"
            )
        refund.reject()
        return refund

    def cancel_refund(self, refund_id: str) -> Refund:
        refund = self._repo.get_refund(refund_id)
        if not refund.can_be_cancelled:
            raise RefundStateError(
                f"Cannot cancel refund in state: {refund.state.value}"
            )
        refund.cancel()
        return refund

    def process_chargeback(
        self,
        payment_id: str,
        refund_id: Optional[str],
        amount: Decimal,
        reason: str,
    ) -> Chargeback:
        if amount <= 0:
            raise InvalidRefundAmountError("Chargeback amount must be positive")

        payment = self._repo.get_payment(payment_id)

        if refund_id is not None:
            refund = self._repo.get_refund(refund_id)
            if refund.payment_id != payment_id:
                raise RefundOwnershipError(
                    f"Refund {refund_id} does not belong to payment {payment_id}"
                )
            if not refund.can_accept_chargeback(amount):
                if amount > refund.remaining_chargeable_amount:
                    raise ChargebackAmountError(
                        f"Chargeback amount {amount} exceeds refund remaining "
                        f"chargeable amount {refund.remaining_chargeable_amount}"
                    )
                raise RefundStateError(
                    f"Cannot charge back refund in state: {refund.state.value}. "
                    f"Remaining chargeable: {refund.remaining_chargeable_amount}"
                )
            needs_rollback = refund.state in (
                RefundState.REFUNDED,
                RefundState.PARTIALLY_CHARGED_BACK,
            )
            if needs_rollback and amount > payment.refunded_amount:
                raise ChargebackAmountError(
                    f"Chargeback amount {amount} exceeds payment refunded amount {payment.refunded_amount}"
                )

            chargeback = make_chargeback(
                payment_id=payment_id,
                refund_id=refund_id,
                amount=amount,
                reason=reason,
            )
            refund.apply_chargeback(chargeback.id, amount)
            if needs_rollback:
                payment.rollback_refunded_amount(amount)
            self._repo.save_chargeback(chargeback)
        else:
            if amount > payment.refunded_amount:
                raise ChargebackAmountError(
                    f"Chargeback amount {amount} exceeds total refunded amount {payment.refunded_amount}"
                )

            all_refunds = self._repo.find_refunds_by_payment_id(payment_id)
            chargeable_refunds = sorted(
                [
                    r
                    for r in all_refunds
                    if r.state
                    in (RefundState.REFUNDED, RefundState.PARTIALLY_CHARGED_BACK)
                ],
                key=lambda r: r.created_at,
            )

            allocation: list[tuple[Refund, Decimal]] = []
            remaining = amount
            for refund in chargeable_refunds:
                if remaining <= 0:
                    break
                alloc_amount = min(refund.remaining_chargeable_amount, remaining)
                if alloc_amount <= 0:
                    continue
                if not refund.can_accept_chargeback(alloc_amount):
                    raise RefundStateError(
                        f"Refund {refund.id} in state {refund.state.value} "
                        f"cannot accept chargeback amount {alloc_amount}"
                    )
                allocation.append((refund, alloc_amount))
                remaining -= alloc_amount

            if remaining > 0:
                raise ChargebackAmountError(
                    f"Cannot allocate full chargeback amount {amount}. "
                    f"Remaining unallocated: {remaining}"
                )

            chargeback = make_chargeback(
                payment_id=payment_id,
                refund_id=None,
                amount=amount,
                reason=reason,
            )

            for refund, alloc_amount in allocation:
                refund.apply_chargeback(chargeback.id, alloc_amount)

            payment.rollback_refunded_amount(amount)
            self._repo.save_chargeback(chargeback)

        payment.chargeback_ids.append(chargeback.id)
        return chargeback

    def get_available_refund_amount(self, payment_id: str) -> Decimal:
        payment = self._repo.get_payment(payment_id)
        return payment.available_refund_amount

    def get_total_refunded_amount(self, payment_id: str) -> Decimal:
        payment = self._repo.get_payment(payment_id)
        return payment.refunded_amount

    def get_total_charged_back_amount(self, payment_id: str) -> Decimal:
        payment = self._repo.get_payment(payment_id)
        return payment.charged_back_amount
