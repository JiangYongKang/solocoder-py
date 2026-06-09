from __future__ import annotations


class RefundError(Exception):
    pass


class PaymentError(RefundError):
    pass


class PaymentNotFoundError(PaymentError):
    pass


class PaymentExistsError(PaymentError):
    pass


class RefundAmountError(RefundError):
    pass


class ExcessRefundError(RefundAmountError):
    def __init__(self, requested: float, available: float) -> None:
        self.requested = requested
        self.available = available
        super().__init__(
            f"Excess refund: requested {requested}, available {available}"
        )


class InvalidRefundAmountError(RefundAmountError):
    pass


class RefundStateError(RefundError):
    pass


class RefundOwnershipError(RefundError):
    pass


class RefundNotFoundError(RefundError):
    pass


class RefundExistsError(RefundError):
    pass


class ChargebackError(RefundError):
    pass


class ChargebackExistsError(ChargebackError):
    pass


class ChargebackAmountError(ChargebackError):
    pass
