import pytest

from solocoder_py.refund import (
    InvalidStateTransitionError,
    RefundState,
    RefundStateMachine,
)


class TestRefundState:
    def test_state_values(self):
        assert RefundState.REFUND_REQUESTED.value == "退款申请"
        assert RefundState.UNDER_REVIEW.value == "审核中"
        assert RefundState.REFUNDED.value == "已退款"
        assert RefundState.REJECTED.value == "已拒绝"
        assert RefundState.CHARGED_BACK.value == "已拒付"
        assert RefundState.CANCELLED.value == "已取消"


class TestRefundStateMachine:
    def test_initial_state(self):
        sm = RefundStateMachine()
        assert sm.state == RefundState.REFUND_REQUESTED

    def test_custom_initial_state(self):
        sm = RefundStateMachine(RefundState.UNDER_REVIEW)
        assert sm.state == RefundState.UNDER_REVIEW

    def test_valid_transitions_from_refund_requested(self):
        sm = RefundStateMachine(RefundState.REFUND_REQUESTED)
        assert sm.can_transition_to(RefundState.UNDER_REVIEW)
        assert sm.can_transition_to(RefundState.CANCELLED)
        assert not sm.can_transition_to(RefundState.REFUNDED)
        assert not sm.can_transition_to(RefundState.REJECTED)
        assert not sm.can_transition_to(RefundState.CHARGED_BACK)

    def test_valid_transitions_from_under_review(self):
        sm = RefundStateMachine(RefundState.UNDER_REVIEW)
        assert sm.can_transition_to(RefundState.REFUNDED)
        assert sm.can_transition_to(RefundState.REJECTED)
        assert sm.can_transition_to(RefundState.CHARGED_BACK)
        assert not sm.can_transition_to(RefundState.REFUND_REQUESTED)
        assert not sm.can_transition_to(RefundState.CANCELLED)

    def test_valid_transitions_from_refunded(self):
        sm = RefundStateMachine(RefundState.REFUNDED)
        assert sm.can_transition_to(RefundState.CHARGED_BACK)
        assert not sm.can_transition_to(RefundState.REFUND_REQUESTED)
        assert not sm.can_transition_to(RefundState.UNDER_REVIEW)
        assert not sm.can_transition_to(RefundState.REJECTED)
        assert not sm.can_transition_to(RefundState.CANCELLED)

    def test_no_transitions_from_rejected(self):
        sm = RefundStateMachine(RefundState.REJECTED)
        assert RefundStateMachine.get_valid_transitions(RefundState.REJECTED) == set()

    def test_no_transitions_from_charged_back(self):
        sm = RefundStateMachine(RefundState.CHARGED_BACK)
        assert sm.get_valid_transitions(RefundState.CHARGED_BACK) == set()

    def test_no_transitions_from_cancelled(self):
        sm = RefundStateMachine(RefundState.CANCELLED)
        assert sm.can_transition_to(RefundState.REFUNDED) is False

    def test_transition_refund_requested_to_under_review(self):
        sm = RefundStateMachine()
        sm.transition_to(RefundState.UNDER_REVIEW)
        assert sm.state == RefundState.UNDER_REVIEW

    def test_transition_refund_requested_to_cancelled(self):
        sm = RefundStateMachine()
        sm.transition_to(RefundState.CANCELLED)
        assert sm.state == RefundState.CANCELLED

    def test_approve_flow_transitions(self):
        sm = RefundStateMachine()
        sm.transition_to(RefundState.UNDER_REVIEW)
        sm.transition_to(RefundState.REFUNDED)
        assert sm.state == RefundState.REFUNDED

    def test_reject_flow_transitions(self):
        sm = RefundStateMachine()
        sm.transition_to(RefundState.UNDER_REVIEW)
        sm.transition_to(RefundState.REJECTED)
        assert sm.state == RefundState.REJECTED

    def test_chargeback_from_under_review(self):
        sm = RefundStateMachine()
        sm.transition_to(RefundState.UNDER_REVIEW)
        sm.transition_to(RefundState.CHARGED_BACK)
        assert sm.state == RefundState.CHARGED_BACK

    def test_chargeback_from_refunded(self):
        sm = RefundStateMachine()
        sm.transition_to(RefundState.UNDER_REVIEW)
        sm.transition_to(RefundState.REFUNDED)
        sm.transition_to(RefundState.CHARGED_BACK)
        assert sm.state == RefundState.CHARGED_BACK

    def test_invalid_transition_raises_error(self):
        sm = RefundStateMachine()
        with pytest.raises(InvalidStateTransitionError) as exc:
            sm.transition_to(RefundState.REFUNDED)
        assert exc.value.current == RefundState.REFUND_REQUESTED
        assert exc.value.target == RefundState.REFUNDED

    def test_cannot_go_back_from_under_review_to_requested(self):
        sm = RefundStateMachine(RefundState.UNDER_REVIEW)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(RefundState.REFUND_REQUESTED)

    def test_cannot_transition_from_rejected(self):
        sm = RefundStateMachine(RefundState.REJECTED)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(RefundState.REFUNDED)

    def test_cannot_transition_from_cancelled(self):
        sm = RefundStateMachine(RefundState.CANCELLED)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(RefundState.UNDER_REVIEW)

    def test_get_valid_transitions_returns_copy(self):
        transitions = RefundStateMachine.get_valid_transitions(
            RefundState.REFUND_REQUESTED
        )
        transitions.add(RefundState.REFUNDED)
        assert RefundState.REFUNDED not in RefundStateMachine.get_valid_transitions(
            RefundState.REFUND_REQUESTED
        )
