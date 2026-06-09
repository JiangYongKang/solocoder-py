from __future__ import annotations

from typing import Dict, List, Optional

from .models import Payment, Refund, Chargeback
from .exceptions import (
    PaymentNotFoundError,
    PaymentExistsError,
    RefundNotFoundError,
    RefundExistsError,
    ChargebackExistsError,
)


class RefundRepository:
    def __init__(self) -> None:
        self._payments: Dict[str, Payment] = {}
        self._refunds: Dict[str, Refund] = {}
        self._chargebacks: Dict[str, Chargeback] = {}

    def save_payment(self, payment: Payment) -> None:
        if payment.id in self._payments:
            raise PaymentExistsError(f"Payment already exists: {payment.id}")
        self._payments[payment.id] = payment

    def find_payment_by_id(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)

    def get_payment(self, payment_id: str) -> Payment:
        payment = self.find_payment_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError(f"Payment not found: {payment_id}")
        return payment

    def find_all_payments(self) -> List[Payment]:
        return list(self._payments.values())

    def save_refund(self, refund: Refund) -> None:
        if refund.id in self._refunds:
            raise RefundExistsError(f"Refund already exists: {refund.id}")
        self._refunds[refund.id] = refund

    def find_refund_by_id(self, refund_id: str) -> Optional[Refund]:
        return self._refunds.get(refund_id)

    def get_refund(self, refund_id: str) -> Refund:
        refund = self.find_refund_by_id(refund_id)
        if refund is None:
            raise RefundNotFoundError(f"Refund not found: {refund_id}")
        return refund

    def find_refunds_by_payment_id(self, payment_id: str) -> List[Refund]:
        return [r for r in self._refunds.values() if r.payment_id == payment_id]

    def find_all_refunds(self) -> List[Refund]:
        return list(self._refunds.values())

    def save_chargeback(self, chargeback: Chargeback) -> None:
        if chargeback.id in self._chargebacks:
            raise ChargebackExistsError(
                f"Chargeback already exists: {chargeback.id}"
            )
        self._chargebacks[chargeback.id] = chargeback

    def find_chargeback_by_id(self, chargeback_id: str) -> Optional[Chargeback]:
        return self._chargebacks.get(chargeback_id)

    def find_chargebacks_by_payment_id(self, payment_id: str) -> List[Chargeback]:
        return [
            cb for cb in self._chargebacks.values() if cb.payment_id == payment_id
        ]

    def find_chargebacks_by_refund_id(self, refund_id: str) -> List[Chargeback]:
        return [
            cb for cb in self._chargebacks.values() if cb.refund_id == refund_id
        ]

    def find_all_chargebacks(self) -> List[Chargeback]:
        return list(self._chargebacks.values())

    def clear(self) -> None:
        self._payments.clear()
        self._refunds.clear()
        self._chargebacks.clear()
