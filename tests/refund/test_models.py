import pytest
from decimal import Decimal

from solocoder_py.refund import (
    Payment,
    Refund,
    Chargeback,
    make_payment,
    make_refund,
    make_chargeback,
    RefundState,
    ExcessRefundError,
    InvalidRefundAmountError,
    ChargebackAmountError,
    InvalidStateTransitionError,
)


class TestPayment:
    def test_payment_creation(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        assert payment.id is not None
        assert payment.user_id == "user-1"
        assert payment.amount == Decimal("100.00")
        assert payment.currency == "CNY"
        assert payment.refunded_amount == 0
        assert payment.charged_back_amount == 0
        assert payment.refund_ids == []
        assert payment.chargeback_ids == []

    def test_payment_with_custom_currency(self):
        payment = make_payment(user_id="user-1", amount=Decimal("10.00"), currency="USD")
        assert payment.currency == "USD"

    def test_payment_amount_must_be_positive(self):
        with pytest.raises(ValueError):
            make_payment(user_id="user-1", amount=Decimal("0"))
        with pytest.raises(ValueError):
            make_payment(user_id="user-1", amount=Decimal("-10.00"))

    def test_available_refund_amount_initial(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        assert payment.available_refund_amount == Decimal("100.00")

    def test_available_refund_amount_after_partial_refund(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("30.00"))
        assert payment.available_refund_amount == Decimal("70.00")

    def test_available_refund_amount_after_full_refund(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("100.00"))
        assert payment.available_refund_amount == 0
        assert payment.is_fully_refunded is True

    def test_available_refund_amount_after_chargeback(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("50.00"))
        payment.rollback_refunded_amount(Decimal("30.00"))
        assert payment.available_refund_amount == Decimal("80.00")
        assert payment.refunded_amount == Decimal("20.00")
        assert payment.charged_back_amount == Decimal("30.00")

    def test_can_refund(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        assert payment.can_refund(Decimal("50.00")) is True
        assert payment.can_refund(Decimal("100.00")) is True
        assert payment.can_refund(Decimal("100.01")) is False
        assert payment.can_refund(Decimal("0")) is False
        assert payment.can_refund(Decimal("-10.00")) is False

    def test_add_refunded_amount(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("30.00"))
        assert payment.refunded_amount == Decimal("30.00")
        payment.add_refunded_amount(Decimal("20.00"))
        assert payment.refunded_amount == Decimal("50.00")

    def test_add_refunded_amount_zero_or_negative(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        with pytest.raises(InvalidRefundAmountError):
            payment.add_refunded_amount(Decimal("0"))
        with pytest.raises(InvalidRefundAmountError):
            payment.add_refunded_amount(Decimal("-10.00"))

    def test_add_refunded_amount_excess(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("80.00"))
        with pytest.raises(ExcessRefundError) as exc:
            payment.add_refunded_amount(Decimal("30.00"))
        assert exc.value.requested == 30.0
        assert exc.value.available == 20.0

    def test_rollback_refunded_amount(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("50.00"))
        payment.rollback_refunded_amount(Decimal("30.00"))
        assert payment.refunded_amount == Decimal("20.00")
        assert payment.charged_back_amount == Decimal("30.00")

    def test_rollback_refunded_amount_zero_or_negative(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("50.00"))
        with pytest.raises(InvalidRefundAmountError):
            payment.rollback_refunded_amount(Decimal("0"))
        with pytest.raises(InvalidRefundAmountError):
            payment.rollback_refunded_amount(Decimal("-10.00"))

    def test_rollback_refunded_amount_exceeds_refunded(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        payment.add_refunded_amount(Decimal("30.00"))
        with pytest.raises(ChargebackAmountError):
            payment.rollback_refunded_amount(Decimal("50.00"))

    def test_is_fully_refunded(self):
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        assert payment.is_fully_refunded is False
        payment.add_refunded_amount(Decimal("100.00"))
        assert payment.is_fully_refunded is True


class TestRefund:
    def test_refund_creation(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"), reason="test")
        assert refund.id is not None
        assert refund.payment_id == "pay-1"
        assert refund.amount == Decimal("50.00")
        assert refund.reason == "test"
        assert refund.state == RefundState.REFUND_REQUESTED
        assert refund.reviewed_at is None
        assert refund.completed_at is None
        assert refund.chargeback_ids == []
        assert refund.charged_back_amount == 0
        assert refund.is_fully_charged_back is False
        assert refund.remaining_chargeable_amount == Decimal("50.00")

    def test_refund_amount_must_be_positive(self):
        with pytest.raises(InvalidRefundAmountError):
            make_refund(payment_id="pay-1", amount=Decimal("0"))
        with pytest.raises(InvalidRefundAmountError):
            make_refund(payment_id="pay-1", amount=Decimal("-10.00"))

    def test_refund_state_flags_initial(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        assert refund.can_be_reviewed is True
        assert refund.can_be_approved is False
        assert refund.can_be_rejected is False
        assert refund.can_be_cancelled is True
        assert refund.can_be_charged_back is False
        assert refund.is_partially_charged_back is False

    def test_start_review(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        assert refund.state == RefundState.UNDER_REVIEW
        assert refund.reviewed_at is not None
        assert refund.can_be_reviewed is False
        assert refund.can_be_approved is True
        assert refund.can_be_rejected is True
        assert refund.can_be_cancelled is False
        assert refund.can_be_charged_back is True

    def test_approve(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        assert refund.state == RefundState.REFUNDED
        assert refund.completed_at is not None
        assert refund.can_be_approved is False
        assert refund.can_be_rejected is False
        assert refund.can_be_charged_back is True

    def test_reject(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.reject()
        assert refund.state == RefundState.REJECTED
        assert refund.completed_at is not None

    def test_cancel(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.cancel()
        assert refund.state == RefundState.CANCELLED
        assert refund.completed_at is not None

    def test_apply_chargeback_from_refunded_full(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        refund.apply_chargeback("cb-1", Decimal("50.00"))
        assert refund.state == RefundState.CHARGED_BACK
        assert "cb-1" in refund.chargeback_ids
        assert refund.charged_back_amount == Decimal("50.00")
        assert refund.is_fully_charged_back is True
        assert refund.remaining_chargeable_amount == 0

    def test_apply_chargeback_from_refunded_partial(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        refund.apply_chargeback("cb-1", Decimal("20.00"))
        assert refund.state == RefundState.PARTIALLY_CHARGED_BACK
        assert "cb-1" in refund.chargeback_ids
        assert refund.charged_back_amount == Decimal("20.00")
        assert refund.is_fully_charged_back is False
        assert refund.is_partially_charged_back is True
        assert refund.remaining_chargeable_amount == Decimal("30.00")

    def test_apply_chargeback_partial_then_remaining(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        refund.apply_chargeback("cb-1", Decimal("20.00"))
        assert refund.state == RefundState.PARTIALLY_CHARGED_BACK
        assert refund.is_partially_charged_back is True
        refund.apply_chargeback("cb-2", Decimal("30.00"))
        assert refund.state == RefundState.CHARGED_BACK
        assert refund.is_partially_charged_back is False
        assert "cb-1" in refund.chargeback_ids
        assert "cb-2" in refund.chargeback_ids
        assert refund.charged_back_amount == Decimal("50.00")
        assert refund.is_fully_charged_back is True

    def test_apply_chargeback_from_under_review_full(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.apply_chargeback("cb-1", Decimal("50.00"))
        assert refund.state == RefundState.CHARGED_BACK
        assert "cb-1" in refund.chargeback_ids
        assert refund.charged_back_amount == Decimal("50.00")
        assert refund.is_fully_charged_back is True

    def test_apply_chargeback_exceeds_remaining(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        with pytest.raises(ChargebackAmountError):
            refund.apply_chargeback("cb-1", Decimal("60.00"))

    def test_apply_chargeback_zero_or_negative(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        with pytest.raises(ChargebackAmountError):
            refund.apply_chargeback("cb-1", Decimal("0"))
        with pytest.raises(ChargebackAmountError):
            refund.apply_chargeback("cb-1", Decimal("-10.00"))

    def test_can_accept_chargeback(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        assert refund.can_accept_chargeback(Decimal("10.00")) is False
        refund.start_review()
        assert refund.can_accept_chargeback(Decimal("50.00")) is True
        assert refund.can_accept_chargeback(Decimal("50.01")) is False
        assert refund.can_accept_chargeback(Decimal("0")) is False
        assert refund.can_accept_chargeback(Decimal("-10")) is False
        refund.apply_chargeback("cb-1", Decimal("20.00"))
        assert refund.can_accept_chargeback(Decimal("30.00")) is True
        assert refund.can_accept_chargeback(Decimal("30.01")) is False

    def test_apply_chargeback_duplicate_chargeback_id_not_duplicated(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        refund.apply_chargeback("cb-1", Decimal("20.00"))
        refund.apply_chargeback("cb-1", Decimal("20.00"))
        assert refund.chargeback_ids == ["cb-1"]
        assert refund.charged_back_amount == Decimal("40.00")

    def test_cannot_approve_from_initial_state(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        with pytest.raises(InvalidStateTransitionError):
            refund.approve()

    def test_cannot_reject_from_initial_state(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        with pytest.raises(InvalidStateTransitionError):
            refund.reject()

    def test_cannot_cancel_from_under_review(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        with pytest.raises(InvalidStateTransitionError):
            refund.cancel()

    def test_apply_chargeback_from_under_review_partial(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.apply_chargeback("cb-1", Decimal("30.00"))
        assert refund.state == RefundState.PARTIALLY_CHARGED_BACK
        assert refund.charged_back_amount == Decimal("30.00")
        assert refund.is_partially_charged_back is True
        assert refund.is_fully_charged_back is False

    def test_apply_chargeback_from_partial_state(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        refund.start_review()
        refund.approve()
        refund.apply_chargeback("cb-1", Decimal("20.00"))
        assert refund.state == RefundState.PARTIALLY_CHARGED_BACK
        assert refund.can_be_charged_back is True
        refund.apply_chargeback("cb-2", Decimal("20.00"))
        assert refund.state == RefundState.PARTIALLY_CHARGED_BACK
        assert refund.charged_back_amount == Decimal("40.00")
        refund.apply_chargeback("cb-3", Decimal("10.00"))
        assert refund.state == RefundState.CHARGED_BACK
        assert refund.is_fully_charged_back is True

    def test_is_partially_charged_back_flags(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("100.00"))
        assert refund.is_partially_charged_back is False
        refund.start_review()
        refund.approve()
        assert refund.is_partially_charged_back is False
        refund.apply_chargeback("cb-1", Decimal("30.00"))
        assert refund.is_partially_charged_back is True
        assert refund.is_fully_charged_back is False
        refund.apply_chargeback("cb-2", Decimal("70.00"))
        assert refund.is_partially_charged_back is False
        assert refund.is_fully_charged_back is True

    def test_can_accept_chargeback_in_partial_state(self):
        refund = make_refund(payment_id="pay-1", amount=Decimal("100.00"))
        refund.start_review()
        refund.approve()
        refund.apply_chargeback("cb-1", Decimal("40.00"))
        assert refund.can_be_charged_back is True
        assert refund.can_accept_chargeback(Decimal("60.00")) is True
        assert refund.can_accept_chargeback(Decimal("60.01")) is False
        assert refund.can_accept_chargeback(Decimal("0")) is False


class TestChargeback:
    def test_chargeback_creation(self):
        cb = make_chargeback(
            payment_id="pay-1",
            refund_id="ref-1",
            amount=Decimal("50.00"),
            reason="fraud",
        )
        assert cb.id is not None
        assert cb.payment_id == "pay-1"
        assert cb.refund_id == "ref-1"
        assert cb.amount == Decimal("50.00")
        assert cb.reason == "fraud"
        assert cb.created_at is not None

    def test_chargeback_without_refund_id(self):
        cb = make_chargeback(
            payment_id="pay-1",
            refund_id=None,
            amount=Decimal("50.00"),
            reason="fraud",
        )
        assert cb.refund_id is None

    def test_chargeback_amount_must_be_positive(self):
        with pytest.raises(ValueError):
            make_chargeback(
                payment_id="pay-1",
                refund_id="ref-1",
                amount=Decimal("0"),
                reason="fraud",
            )
        with pytest.raises(ValueError):
            make_chargeback(
                payment_id="pay-1",
                refund_id="ref-1",
                amount=Decimal("-10.00"),
                reason="fraud",
            )
