import pytest
from decimal import Decimal

from solocoder_py.refund import (
    RefundRepository,
    make_payment,
    make_refund,
    make_chargeback,
    PaymentNotFoundError,
    PaymentExistsError,
    RefundNotFoundError,
    RefundExistsError,
    ChargebackExistsError,
)


class TestRefundRepository:
    def test_save_and_find_payment(self):
        repo = RefundRepository()
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        repo.save_payment(payment)
        found = repo.find_payment_by_id(payment.id)
        assert found is not None
        assert found.id == payment.id
        assert found.amount == Decimal("100.00")

    def test_get_payment_not_found(self):
        repo = RefundRepository()
        with pytest.raises(PaymentNotFoundError):
            repo.get_payment("non-existent")

    def test_save_duplicate_payment(self):
        repo = RefundRepository()
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        repo.save_payment(payment)
        with pytest.raises(PaymentExistsError):
            repo.save_payment(payment)

    def test_find_all_payments(self):
        repo = RefundRepository()
        p1 = make_payment(user_id="user-1", amount=Decimal("100.00"))
        p2 = make_payment(user_id="user-2", amount=Decimal("200.00"))
        repo.save_payment(p1)
        repo.save_payment(p2)
        all_payments = repo.find_all_payments()
        assert len(all_payments) == 2

    def test_save_and_find_refund(self):
        repo = RefundRepository()
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        repo.save_refund(refund)
        found = repo.find_refund_by_id(refund.id)
        assert found is not None
        assert found.id == refund.id

    def test_get_refund_not_found(self):
        repo = RefundRepository()
        with pytest.raises(RefundNotFoundError):
            repo.get_refund("non-existent")

    def test_save_duplicate_refund(self):
        repo = RefundRepository()
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        repo.save_refund(refund)
        with pytest.raises(RefundExistsError):
            repo.save_refund(refund)

    def test_find_refunds_by_payment_id(self):
        repo = RefundRepository()
        r1 = make_refund(payment_id="pay-1", amount=Decimal("30.00"))
        r2 = make_refund(payment_id="pay-1", amount=Decimal("20.00"))
        r3 = make_refund(payment_id="pay-2", amount=Decimal("10.00"))
        repo.save_refund(r1)
        repo.save_refund(r2)
        repo.save_refund(r3)
        results = repo.find_refunds_by_payment_id("pay-1")
        assert len(results) == 2
        results = repo.find_refunds_by_payment_id("pay-2")
        assert len(results) == 1

    def test_find_all_refunds(self):
        repo = RefundRepository()
        r1 = make_refund(payment_id="pay-1", amount=Decimal("30.00"))
        r2 = make_refund(payment_id="pay-1", amount=Decimal("20.00"))
        repo.save_refund(r1)
        repo.save_refund(r2)
        all_refunds = repo.find_all_refunds()
        assert len(all_refunds) == 2

    def test_save_and_find_chargeback(self):
        repo = RefundRepository()
        cb = make_chargeback(
            payment_id="pay-1",
            refund_id="ref-1",
            amount=Decimal("30.00"),
            reason="fraud",
        )
        repo.save_chargeback(cb)
        found = repo.find_chargeback_by_id(cb.id)
        assert found is not None
        assert found.id == cb.id

    def test_save_duplicate_chargeback(self):
        repo = RefundRepository()
        cb = make_chargeback(
            payment_id="pay-1",
            refund_id="ref-1",
            amount=Decimal("30.00"),
            reason="fraud",
        )
        repo.save_chargeback(cb)
        with pytest.raises(ChargebackExistsError):
            repo.save_chargeback(cb)

    def test_find_chargebacks_by_payment_id(self):
        repo = RefundRepository()
        cb1 = make_chargeback(
            payment_id="pay-1",
            refund_id="ref-1",
            amount=Decimal("30.00"),
            reason="fraud",
        )
        cb2 = make_chargeback(
            payment_id="pay-2",
            refund_id=None,
            amount=Decimal("20.00"),
            reason="other",
        )
        repo.save_chargeback(cb1)
        repo.save_chargeback(cb2)
        results = repo.find_chargebacks_by_payment_id("pay-1")
        assert len(results) == 1

    def test_find_chargebacks_by_refund_id(self):
        repo = RefundRepository()
        cb1 = make_chargeback(
            payment_id="pay-1",
            refund_id="ref-1",
            amount=Decimal("30.00"),
            reason="fraud",
        )
        cb2 = make_chargeback(
            payment_id="pay-1",
            refund_id="ref-2",
            amount=Decimal("20.00"),
            reason="other",
        )
        repo.save_chargeback(cb1)
        repo.save_chargeback(cb2)
        results = repo.find_chargebacks_by_refund_id("ref-1")
        assert len(results) == 1
        assert results[0].refund_id == "ref-1"

    def test_find_all_chargebacks(self):
        repo = RefundRepository()
        cb1 = make_chargeback(
            payment_id="pay-1",
            refund_id="ref-1",
            amount=Decimal("30.00"),
            reason="fraud",
        )
        cb2 = make_chargeback(
            payment_id="pay-2",
            refund_id=None,
            amount=Decimal("20.00"),
            reason="other",
        )
        repo.save_chargeback(cb1)
        repo.save_chargeback(cb2)
        all_cbs = repo.find_all_chargebacks()
        assert len(all_cbs) == 2

    def test_clear(self):
        repo = RefundRepository()
        payment = make_payment(user_id="user-1", amount=Decimal("100.00"))
        refund = make_refund(payment_id="pay-1", amount=Decimal("50.00"))
        cb = make_chargeback(
            payment_id="pay-1",
            refund_id=None,
            amount=Decimal("30.00"),
            reason="fraud",
        )
        repo.save_payment(payment)
        repo.save_refund(refund)
        repo.save_chargeback(cb)
        repo.clear()
        assert len(repo.find_all_payments()) == 0
        assert len(repo.find_all_refunds()) == 0
        assert len(repo.find_all_chargebacks()) == 0
