from decimal import Decimal

from solocoder_py.refund import (
    RefundEngine,
    RefundRepository,
    make_payment,
    make_refund,
    Payment,
    Refund,
)


def make_payment_for_test(
    user_id: str = "user-1",
    amount: Decimal = Decimal("1000.00"),
    currency: str = "CNY",
) -> Payment:
    return make_payment(user_id=user_id, amount=amount, currency=currency)


def make_refund_for_test(
    payment_id: str = "pay-1",
    amount: Decimal = Decimal("100.00"),
    reason: str = "test refund",
) -> Refund:
    return make_refund(payment_id=payment_id, amount=amount, reason=reason)


def make_engine_with_payment(
    amount: Decimal = Decimal("1000.00"),
) -> tuple[RefundEngine, Payment]:
    engine = RefundEngine(RefundRepository())
    payment = engine.create_payment(user_id="user-1", amount=amount)
    return engine, payment
