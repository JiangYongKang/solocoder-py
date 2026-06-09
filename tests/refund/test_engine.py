import pytest
from decimal import Decimal

from solocoder_py.refund import (
    RefundEngine,
    RefundRepository,
    RefundState,
    ExcessRefundError,
    InvalidRefundAmountError,
    RefundStateError,
    RefundOwnershipError,
    ChargebackAmountError,
    PaymentNotFoundError,
)


class TestRefundEngineNormalFlow:
    def test_create_payment(self):
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        assert payment.user_id == "user-1"
        assert payment.amount == Decimal("1000.00")

    def test_request_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(
            payment_id=payment.id,
            amount=Decimal("300.00"),
            reason="quality issue",
        )
        assert refund.payment_id == payment.id
        assert refund.amount == Decimal("300.00")
        assert refund.state == RefundState.REFUND_REQUESTED

    def test_start_review(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        refund = engine.repository.get_refund(refund.id)
        assert refund.state == RefundState.UNDER_REVIEW
        assert refund.reviewed_at is not None

    def test_approve_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)
        refund = engine.repository.get_refund(refund.id)
        assert refund.state == RefundState.REFUNDED
        assert refund.completed_at is not None
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("300.00")

    def test_reject_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.reject_refund(refund.id)
        refund = engine.repository.get_refund(refund.id)
        assert refund.state == RefundState.REJECTED
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == 0

    def test_cancel_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.cancel_refund(refund.id)
        refund = engine.repository.get_refund(refund.id)
        assert refund.state == RefundState.CANCELLED


class TestPartialRefund:
    def test_multiple_partial_refunds(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))

        r1 = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(r1.id)
        engine.approve_refund(r1.id)
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("300.00")
        assert payment.available_refund_amount == Decimal("700.00")

        r2 = engine.request_refund(payment.id, Decimal("200.00"))
        engine.start_review(r2.id)
        engine.approve_refund(r2.id)
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("500.00")
        assert payment.available_refund_amount == Decimal("500.00")

        r3 = engine.request_refund(payment.id, Decimal("500.00"))
        engine.start_review(r3.id)
        engine.approve_refund(r3.id)
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("1000.00")
        assert payment.available_refund_amount == 0
        assert payment.is_fully_refunded is True

    def test_refund_amount_exactly_equals_payment(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("500.00"))
        refund = engine.request_refund(payment.id, Decimal("500.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("500.00")
        assert payment.available_refund_amount == 0

    def test_multiple_refunds_sum_to_payment(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("100.00"))

        for i in range(10):
            refund = engine.request_refund(payment.id, Decimal("10.00"))
            engine.start_review(refund.id)
            engine.approve_refund(refund.id)

        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("100.00")
        assert payment.available_refund_amount == 0

    def test_excess_refund_rejected(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("100.00"))

        r1 = engine.request_refund(payment.id, Decimal("60.00"))
        engine.start_review(r1.id)
        engine.approve_refund(r1.id)

        with pytest.raises(ExcessRefundError) as exc:
            engine.request_refund(payment.id, Decimal("50.00"))
        assert exc.value.requested == 50.0
        assert exc.value.available == 40.0

    def test_excess_refund_at_request_time(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("100.00"))
        with pytest.raises(ExcessRefundError):
            engine.request_refund(payment.id, Decimal("150.00"))

    def test_cannot_request_after_full_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("100.00"))
        refund = engine.request_refund(payment.id, Decimal("100.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)
        with pytest.raises(ExcessRefundError):
            engine.request_refund(payment.id, Decimal("1.00"))

    def test_negative_refund_amount_rejected(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("100.00"))
        with pytest.raises(InvalidRefundAmountError):
            engine.request_refund(payment.id, Decimal("-10.00"))

    def test_zero_refund_amount_rejected(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("100.00"))
        with pytest.raises(InvalidRefundAmountError):
            engine.request_refund(payment.id, Decimal("0"))

    def test_get_available_refund_amount(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        assert engine.get_available_refund_amount(payment.id) == Decimal("1000.00")
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)
        assert engine.get_available_refund_amount(payment.id) == Decimal("700.00")
        assert engine.get_total_refunded_amount(payment.id) == Decimal("300.00")


class TestChargeback:
    def test_chargeback_on_refunded_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("500.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("500.00")
        assert payment.available_refund_amount == Decimal("500.00")

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=refund.id,
            amount=Decimal("500.00"),
            reason="fraud",
        )

        refund = engine.repository.get_refund(refund.id)
        assert refund.state == RefundState.CHARGED_BACK

        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == 0
        assert payment.charged_back_amount == Decimal("500.00")
        assert payment.available_refund_amount == Decimal("1000.00")

    def test_chargeback_partial_amount(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("500.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=refund.id,
            amount=Decimal("200.00"),
            reason="partial dispute",
        )

        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("300.00")
        assert payment.charged_back_amount == Decimal("200.00")
        assert payment.available_refund_amount == Decimal("700.00")

    def test_chargeback_on_under_review_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("500.00"))
        engine.start_review(refund.id)

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=refund.id,
            amount=Decimal("500.00"),
            reason="fraud",
        )

        refund = engine.repository.get_refund(refund.id)
        assert refund.state == RefundState.CHARGED_BACK
        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == 0

    def test_chargeback_without_refund_id_updates_refund_states(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund1 = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund1.id)
        engine.approve_refund(refund1.id)
        refund2 = engine.request_refund(payment.id, Decimal("400.00"))
        engine.start_review(refund2.id)
        engine.approve_refund(refund2.id)

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=None,
            amount=Decimal("500.00"),
            reason="fraud",
        )

        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("200.00")
        assert payment.charged_back_amount == Decimal("500.00")
        assert payment.available_refund_amount == Decimal("800.00")

        r1 = engine.repository.get_refund(refund1.id)
        r2 = engine.repository.get_refund(refund2.id)
        assert r1.state == RefundState.CHARGED_BACK
        assert r1.chargeback_id == cb.id
        assert r2.state == RefundState.CHARGED_BACK
        assert r2.chargeback_id == cb.id

    def test_chargeback_without_refund_id_partial_first_refund_only(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund1 = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund1.id)
        engine.approve_refund(refund1.id)
        refund2 = engine.request_refund(payment.id, Decimal("400.00"))
        engine.start_review(refund2.id)
        engine.approve_refund(refund2.id)

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=None,
            amount=Decimal("200.00"),
            reason="partial dispute",
        )

        r1 = engine.repository.get_refund(refund1.id)
        r2 = engine.repository.get_refund(refund2.id)
        assert r1.state == RefundState.CHARGED_BACK
        assert r1.chargeback_id == cb.id
        assert r2.state == RefundState.REFUNDED
        assert r2.chargeback_id is None

    def test_chargeback_without_refund_id_covers_exactly_all_refunds(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund1 = engine.request_refund(payment.id, Decimal("200.00"))
        engine.start_review(refund1.id)
        engine.approve_refund(refund1.id)
        refund2 = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund2.id)
        engine.approve_refund(refund2.id)

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=None,
            amount=Decimal("500.00"),
            reason="full dispute",
        )

        r1 = engine.repository.get_refund(refund1.id)
        r2 = engine.repository.get_refund(refund2.id)
        assert r1.state == RefundState.CHARGED_BACK
        assert r2.state == RefundState.CHARGED_BACK
        assert engine.get_total_refunded_amount(payment.id) == 0

    def test_chargeback_without_refund_id_ignores_non_refunded_states(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund1 = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund1.id)
        engine.approve_refund(refund1.id)
        refund2 = engine.request_refund(payment.id, Decimal("200.00"))
        engine.start_review(refund2.id)
        engine.reject_refund(refund2.id)
        refund3 = engine.request_refund(payment.id, Decimal("100.00"))
        engine.cancel_refund(refund3.id)

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=None,
            amount=Decimal("300.00"),
            reason="fraud",
        )

        r1 = engine.repository.get_refund(refund1.id)
        r2 = engine.repository.get_refund(refund2.id)
        r3 = engine.repository.get_refund(refund3.id)
        assert r1.state == RefundState.CHARGED_BACK
        assert r2.state == RefundState.REJECTED
        assert r3.state == RefundState.CANCELLED

    def test_refund_ownership_error_distinct_from_state_error(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment1 = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        payment2 = engine.create_payment(user_id="user-2", amount=Decimal("500.00"))
        refund = engine.request_refund(payment1.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)

        try:
            engine.process_chargeback(
                payment_id=payment2.id,
                refund_id=refund.id,
                amount=Decimal("300.00"),
                reason="fraud",
            )
        except RefundOwnershipError as e:
            assert "does not belong to payment" in str(e)
            assert isinstance(e, RefundOwnershipError)
            assert not isinstance(e, RefundStateError)
        else:
            pytest.fail("Expected RefundOwnershipError was not raised")

    def test_chargeback_rollback_allows_new_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("500.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)

        cb = engine.process_chargeback(
            payment_id=payment.id,
            refund_id=refund.id,
            amount=Decimal("500.00"),
            reason="fraud",
        )

        new_refund = engine.request_refund(payment.id, Decimal("800.00"))
        engine.start_review(new_refund.id)
        engine.approve_refund(new_refund.id)

        payment = engine.repository.get_payment(payment.id)
        assert payment.refunded_amount == Decimal("800.00")
        assert payment.available_refund_amount == Decimal("200.00")

    def test_chargeback_amount_exceeds_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)

        with pytest.raises(ChargebackAmountError):
            engine.process_chargeback(
                payment_id=payment.id,
                refund_id=refund.id,
                amount=Decimal("500.00"),
                reason="fraud",
            )

    def test_chargeback_amount_exceeds_total_refunded(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)

        with pytest.raises(ChargebackAmountError):
            engine.process_chargeback(
                payment_id=payment.id,
                refund_id=None,
                amount=Decimal("500.00"),
                reason="fraud",
            )

    def test_chargeback_on_rejected_refund_fails(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.reject_refund(refund.id)

        with pytest.raises(RefundStateError):
            engine.process_chargeback(
                payment_id=payment.id,
                refund_id=refund.id,
                amount=Decimal("300.00"),
                reason="fraud",
            )

    def test_chargeback_negative_amount(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)

        with pytest.raises(InvalidRefundAmountError):
            engine.process_chargeback(
                payment_id=payment.id,
                refund_id=refund.id,
                amount=Decimal("-100.00"),
                reason="fraud",
            )

    def test_chargeback_refund_belongs_to_another_payment(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment1 = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        payment2 = engine.create_payment(user_id="user-2", amount=Decimal("500.00"))
        refund = engine.request_refund(payment1.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.approve_refund(refund.id)

        with pytest.raises(RefundOwnershipError):
            engine.process_chargeback(
                payment_id=payment2.id,
                refund_id=refund.id,
                amount=Decimal("300.00"),
                reason="fraud",
            )


class TestInvalidTransitions:
    def test_cannot_approve_without_review(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))

        with pytest.raises(RefundStateError):
            engine.approve_refund(refund.id)

    def test_cannot_reject_without_review(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))

        with pytest.raises(RefundStateError):
            engine.reject_refund(refund.id)

    def test_cannot_cancel_after_review_starts(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)

        with pytest.raises(RefundStateError):
            engine.cancel_refund(refund.id)

    def test_cannot_start_review_twice(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)

        with pytest.raises(RefundStateError):
            engine.start_review(refund.id)

    def test_cannot_approve_rejected_refund(self):
        engine, payment = RefundEngine(RefundRepository()), None
        engine = RefundEngine(RefundRepository())
        payment = engine.create_payment(user_id="user-1", amount=Decimal("1000.00"))
        refund = engine.request_refund(payment.id, Decimal("300.00"))
        engine.start_review(refund.id)
        engine.reject_refund(refund.id)

        with pytest.raises(RefundStateError):
            engine.approve_refund(refund.id)

    def test_request_refund_payment_not_found(self):
        engine = RefundEngine(RefundRepository())
        with pytest.raises(PaymentNotFoundError):
            engine.request_refund("non-existent-payment", Decimal("100.00"))
