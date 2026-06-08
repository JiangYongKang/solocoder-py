import pytest

from solocoder_py.subscription import (
    InvalidStateTransitionError,
    SubscriptionState,
    SubscriptionStateMachine,
)


class TestSubscriptionState:
    def test_state_values(self):
        assert SubscriptionState.TRIAL.value == "试用"
        assert SubscriptionState.ACTIVE.value == "活跃"
        assert SubscriptionState.PAUSED.value == "暂停"
        assert SubscriptionState.DOWNGRADE_PENDING.value == "降级处理中"
        assert SubscriptionState.CANCELLED.value == "已取消"
        assert SubscriptionState.EXPIRED.value == "已过期"


class TestSubscriptionStateMachine:
    def test_initial_state(self):
        sm = SubscriptionStateMachine()
        assert sm.state == SubscriptionState.TRIAL

    def test_custom_initial_state(self):
        sm = SubscriptionStateMachine(SubscriptionState.ACTIVE)
        assert sm.state == SubscriptionState.ACTIVE

    def test_valid_transitions_from_trial(self):
        sm = SubscriptionStateMachine(SubscriptionState.TRIAL)
        assert sm.can_transition_to(SubscriptionState.ACTIVE)
        assert sm.can_transition_to(SubscriptionState.CANCELLED)
        assert sm.can_transition_to(SubscriptionState.EXPIRED)
        assert not sm.can_transition_to(SubscriptionState.PAUSED)
        assert not sm.can_transition_to(SubscriptionState.DOWNGRADE_PENDING)

    def test_valid_transitions_from_active(self):
        sm = SubscriptionStateMachine(SubscriptionState.ACTIVE)
        assert sm.can_transition_to(SubscriptionState.ACTIVE)
        assert sm.can_transition_to(SubscriptionState.PAUSED)
        assert sm.can_transition_to(SubscriptionState.DOWNGRADE_PENDING)
        assert sm.can_transition_to(SubscriptionState.CANCELLED)
        assert sm.can_transition_to(SubscriptionState.EXPIRED)
        assert not sm.can_transition_to(SubscriptionState.TRIAL)

    def test_valid_transitions_from_paused(self):
        sm = SubscriptionStateMachine(SubscriptionState.PAUSED)
        assert sm.can_transition_to(SubscriptionState.ACTIVE)
        assert sm.can_transition_to(SubscriptionState.DOWNGRADE_PENDING)
        assert sm.can_transition_to(SubscriptionState.CANCELLED)
        assert sm.can_transition_to(SubscriptionState.EXPIRED)
        assert not sm.can_transition_to(SubscriptionState.TRIAL)

    def test_valid_transitions_from_downgrade_pending(self):
        sm = SubscriptionStateMachine(SubscriptionState.DOWNGRADE_PENDING)
        assert sm.can_transition_to(SubscriptionState.ACTIVE)
        assert sm.can_transition_to(SubscriptionState.PAUSED)
        assert sm.can_transition_to(SubscriptionState.CANCELLED)
        assert sm.can_transition_to(SubscriptionState.EXPIRED)
        assert not sm.can_transition_to(SubscriptionState.TRIAL)

    def test_valid_transitions_from_cancelled(self):
        sm = SubscriptionStateMachine(SubscriptionState.CANCELLED)
        assert sm.can_transition_to(SubscriptionState.EXPIRED)
        assert not sm.can_transition_to(SubscriptionState.ACTIVE)
        assert not sm.can_transition_to(SubscriptionState.PAUSED)

    def test_no_transitions_from_expired(self):
        sm = SubscriptionStateMachine(SubscriptionState.EXPIRED)
        assert SubscriptionStateMachine.get_valid_transitions(SubscriptionState.EXPIRED) == set()

    def test_transition_trial_to_active(self):
        sm = SubscriptionStateMachine()
        sm.transition_to(SubscriptionState.ACTIVE)
        assert sm.state == SubscriptionState.ACTIVE

    def test_transition_trial_to_cancelled(self):
        sm = SubscriptionStateMachine()
        sm.transition_to(SubscriptionState.CANCELLED)
        assert sm.state == SubscriptionState.CANCELLED

    def test_full_lifecycle_transitions(self):
        sm = SubscriptionStateMachine()
        sm.transition_to(SubscriptionState.ACTIVE)
        sm.transition_to(SubscriptionState.PAUSED)
        sm.transition_to(SubscriptionState.ACTIVE)
        sm.transition_to(SubscriptionState.DOWNGRADE_PENDING)
        sm.transition_to(SubscriptionState.ACTIVE)
        sm.transition_to(SubscriptionState.CANCELLED)
        sm.transition_to(SubscriptionState.EXPIRED)
        assert sm.state == SubscriptionState.EXPIRED

    def test_invalid_transition_raises_error(self):
        sm = SubscriptionStateMachine()
        with pytest.raises(InvalidStateTransitionError) as exc:
            sm.transition_to(SubscriptionState.PAUSED)
        assert exc.value.current == SubscriptionState.TRIAL
        assert exc.value.target == SubscriptionState.PAUSED

    def test_cannot_go_back_from_active_to_trial(self):
        sm = SubscriptionStateMachine(SubscriptionState.ACTIVE)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(SubscriptionState.TRIAL)

    def test_cannot_transition_from_expired(self):
        sm = SubscriptionStateMachine(SubscriptionState.EXPIRED)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(SubscriptionState.ACTIVE)

    def test_cannot_transition_from_cancelled_to_active(self):
        sm = SubscriptionStateMachine(SubscriptionState.CANCELLED)
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(SubscriptionState.ACTIVE)

    def test_get_valid_transitions_returns_copy(self):
        transitions = SubscriptionStateMachine.get_valid_transitions(SubscriptionState.ACTIVE)
        transitions.add(SubscriptionState.TRIAL)
        assert SubscriptionState.TRIAL not in SubscriptionStateMachine.get_valid_transitions(
            SubscriptionState.ACTIVE
        )

    def test_set_state_bypasses_validation(self):
        sm = SubscriptionStateMachine(SubscriptionState.EXPIRED)
        sm.set_state(SubscriptionState.ACTIVE)
        assert sm.state == SubscriptionState.ACTIVE
