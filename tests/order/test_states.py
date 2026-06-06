import pytest

from solocoder_py.order import (
    InvalidStateTransitionError,
    OrderState,
    OrderStateMachine,
)


class TestOrderState:
    def test_state_values(self):
        assert OrderState.PENDING_PAYMENT.value == "待支付"
        assert OrderState.PAID.value == "已支付"
        assert OrderState.SHIPPED.value == "已发货"
        assert OrderState.DELIVERED.value == "已签收"
        assert OrderState.COMPLETED.value == "已完成"
        assert OrderState.CANCELLED.value == "已取消"
        assert OrderState.REFUNDING.value == "退款中"
        assert OrderState.REFUNDED.value == "已退款"
        assert OrderState.AFTER_SALE.value == "售后中"


class TestOrderStateMachine:
    def test_initial_state(self):
        sm = OrderStateMachine()
        assert sm.state == OrderState.PENDING_PAYMENT

    def test_custom_initial_state(self):
        sm = OrderStateMachine(OrderState.PAID)
        assert sm.state == OrderState.PAID

    def test_valid_transitions_from_pending_payment(self):
        sm = OrderStateMachine(OrderState.PENDING_PAYMENT)
        assert sm.can_transition_to(OrderState.PAID)
        assert sm.can_transition_to(OrderState.CANCELLED)
        assert not sm.can_transition_to(OrderState.SHIPPED)
        assert not sm.can_transition_to(OrderState.DELIVERED)

    def test_valid_transitions_from_paid(self):
        sm = OrderStateMachine(OrderState.PAID)
        assert sm.can_transition_to(OrderState.SHIPPED)
        assert sm.can_transition_to(OrderState.REFUNDING)
        assert not sm.can_transition_to(OrderState.PENDING_PAYMENT)

    def test_valid_transitions_from_shipped(self):
        sm = OrderStateMachine(OrderState.SHIPPED)
        assert sm.can_transition_to(OrderState.DELIVERED)
        assert not sm.can_transition_to(OrderState.PAID)

    def test_valid_transitions_from_delivered(self):
        sm = OrderStateMachine(OrderState.DELIVERED)
        assert sm.can_transition_to(OrderState.COMPLETED)
        assert sm.can_transition_to(OrderState.AFTER_SALE)

    def test_no_transitions_from_completed(self):
        sm = OrderStateMachine(OrderState.COMPLETED)
        assert sm.get_valid_transitions(OrderState.COMPLETED) == set()

    def test_no_transitions_from_cancelled(self):
        sm = OrderStateMachine(OrderState.CANCELLED)
        assert OrderStateMachine.get_valid_transitions(OrderState.CANCELLED) == set()

    def test_no_transitions_from_refunded(self):
        sm = OrderStateMachine(OrderState.REFUNDED)
        assert sm.can_transition_to(OrderState.PAID) is False

    def test_transition_pending_to_paid(self):
        sm = OrderStateMachine()
        sm.transition_to(OrderState.PAID)
        assert sm.state == OrderState.PAID

    def test_transition_pending_to_cancelled(self):
        sm = OrderStateMachine()
        sm.transition_to(OrderState.CANCELLED)
        assert sm.state == OrderState.CANCELLED

    def test_full_lifecycle_transitions(self):
        sm = OrderStateMachine()
        sm.transition_to(OrderState.PAID)
        sm.transition_to(OrderState.SHIPPED)
        sm.transition_to(OrderState.DELIVERED)
        sm.transition_to(OrderState.COMPLETED)
        assert sm.state == OrderState.COMPLETED

    def test_refund_flow_transitions(self):
        sm = OrderStateMachine(OrderState.PAID)
        sm.transition_to(OrderState.REFUNDING)
        sm.transition_to(OrderState.REFUNDED)
        assert sm.state == OrderState.REFUNDED

    def test_after_sale_flow_transitions(self):
        sm = OrderStateMachine(OrderState.DELIVERED)
        sm.transition_to(OrderState.AFTER_SALE)
        sm.transition_to(OrderState.COMPLETED)
        assert sm.state == OrderState.COMPLETED

    def test_after_sale_to_refunded(self):
        sm = OrderStateMachine(OrderState.DELIVERED)
        sm.transition_to(OrderState.AFTER_SALE)
        sm.transition_to(OrderState.REFUNDED)
        assert sm.state == OrderState.REFUNDED

    def test_invalid_transition_raises_error(self):
        sm = OrderStateMachine()
        with pytest.raises(InvalidStateTransitionError) as exc:
            sm.transition_to(OrderState.SHIPPED)
        assert exc.value.current == OrderState.PENDING_PAYMENT
        assert exc.value.target == OrderState.SHIPPED

    def test_cannot_go_back_from_paid_to_pending(self):
        sm = OrderStateMachine(OrderState.PAID)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(OrderState.PENDING_PAYMENT)

    def test_cannot_transition_from_completed(self):
        sm = OrderStateMachine(OrderState.COMPLETED)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(OrderState.DELIVERED)

    def test_get_valid_transitions_returns_copy(self):
        transitions = OrderStateMachine.get_valid_transitions(OrderState.PENDING_PAYMENT)
        transitions.add(OrderState.DELIVERED)
        assert OrderState.DELIVERED not in OrderStateMachine.get_valid_transitions(
            OrderState.PENDING_PAYMENT
        )
