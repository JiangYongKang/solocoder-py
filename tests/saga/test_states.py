from __future__ import annotations

import pytest

from solocoder_py.saga import (
    IllegalStateTransitionError,
    SagaInstanceStatus,
    SagaStateMachine,
    StepCompensationStatus,
    StepExecutionStatus,
)


class TestStepStatusEnums:
    def test_execution_status_values(self) -> None:
        assert StepExecutionStatus.PENDING.value == "pending"
        assert StepExecutionStatus.RUNNING.value == "running"
        assert StepExecutionStatus.COMPLETED.value == "completed"
        assert StepExecutionStatus.FAILED.value == "failed"

    def test_compensation_status_values(self) -> None:
        assert StepCompensationStatus.NONE.value == "none"
        assert StepCompensationStatus.PENDING.value == "pending"
        assert StepCompensationStatus.RUNNING.value == "running"
        assert StepCompensationStatus.COMPLETED.value == "completed"
        assert StepCompensationStatus.FAILED.value == "failed"
        assert StepCompensationStatus.SKIPPED.value == "skipped"

    def test_saga_instance_status_values(self) -> None:
        assert SagaInstanceStatus.PENDING.value == "pending"
        assert SagaInstanceStatus.RUNNING.value == "running"
        assert SagaInstanceStatus.COMPLETED.value == "completed"
        assert SagaInstanceStatus.FAILED.value == "failed"
        assert SagaInstanceStatus.COMPENSATING.value == "compensating"
        assert SagaInstanceStatus.COMPENSATED.value == "compensated"
        assert SagaInstanceStatus.COMPENSATION_FAILED.value == "compensation_failed"
        assert SagaInstanceStatus.ABORTED.value == "aborted"


class TestSagaStateMachine:
    def test_initial_state(self) -> None:
        sm = SagaStateMachine()
        assert sm.state == SagaInstanceStatus.PENDING

    def test_custom_initial_state(self) -> None:
        sm = SagaStateMachine(SagaInstanceStatus.RUNNING)
        assert sm.state == SagaInstanceStatus.RUNNING

    def test_valid_transitions_from_pending(self) -> None:
        sm = SagaStateMachine()
        assert sm.can_transition_to(SagaInstanceStatus.RUNNING) is True
        assert sm.can_transition_to(SagaInstanceStatus.ABORTED) is True
        assert sm.can_transition_to(SagaInstanceStatus.COMPLETED) is False

    def test_valid_transitions_from_running(self) -> None:
        sm = SagaStateMachine(SagaInstanceStatus.RUNNING)
        assert sm.can_transition_to(SagaInstanceStatus.COMPLETED) is True
        assert sm.can_transition_to(SagaInstanceStatus.FAILED) is True
        assert sm.can_transition_to(SagaInstanceStatus.ABORTED) is True
        assert sm.can_transition_to(SagaInstanceStatus.COMPENSATING) is False

    def test_valid_transitions_from_failed(self) -> None:
        sm = SagaStateMachine(SagaInstanceStatus.FAILED)
        assert sm.can_transition_to(SagaInstanceStatus.COMPENSATING) is True
        assert sm.can_transition_to(SagaInstanceStatus.COMPENSATED) is False

    def test_valid_transitions_from_compensating(self) -> None:
        sm = SagaStateMachine(SagaInstanceStatus.COMPENSATING)
        assert sm.can_transition_to(SagaInstanceStatus.COMPENSATED) is True
        assert sm.can_transition_to(SagaInstanceStatus.COMPENSATION_FAILED) is True
        assert sm.can_transition_to(SagaInstanceStatus.RUNNING) is False

    def test_terminal_states_have_no_outgoing_transitions(self) -> None:
        for status in [
            SagaInstanceStatus.COMPLETED,
            SagaInstanceStatus.COMPENSATED,
            SagaInstanceStatus.COMPENSATION_FAILED,
            SagaInstanceStatus.ABORTED,
        ]:
            sm = SagaStateMachine(status)
            assert len([t for t in SagaInstanceStatus if sm.can_transition_to(t)]) == 0

    def test_transition_to_valid_state(self) -> None:
        sm = SagaStateMachine()
        sm.transition_to(SagaInstanceStatus.RUNNING)
        assert sm.state == SagaInstanceStatus.RUNNING

    def test_transition_to_invalid_state_raises(self) -> None:
        sm = SagaStateMachine()
        with pytest.raises(IllegalStateTransitionError) as exc_info:
            sm.transition_to(SagaInstanceStatus.COMPLETED)
        assert exc_info.value.current == SagaInstanceStatus.PENDING
        assert exc_info.value.target == SagaInstanceStatus.COMPLETED

    def test_transition_from_terminal_state_raises(self) -> None:
        sm = SagaStateMachine(SagaInstanceStatus.COMPLETED)
        with pytest.raises(IllegalStateTransitionError):
            sm.transition_to(SagaInstanceStatus.RUNNING)

    def test_is_terminal(self) -> None:
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.COMPLETED) is True
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.COMPENSATED) is True
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.COMPENSATION_FAILED) is True
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.ABORTED) is True
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.PENDING) is False
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.RUNNING) is False
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.FAILED) is False
        assert SagaStateMachine.is_terminal(SagaInstanceStatus.COMPENSATING) is False

    def test_full_valid_lifecycle_transitions(self) -> None:
        sm = SagaStateMachine()
        sm.transition_to(SagaInstanceStatus.RUNNING)
        sm.transition_to(SagaInstanceStatus.COMPLETED)
        assert sm.state == SagaInstanceStatus.COMPLETED

    def test_full_failed_lifecycle_transitions(self) -> None:
        sm = SagaStateMachine()
        sm.transition_to(SagaInstanceStatus.RUNNING)
        sm.transition_to(SagaInstanceStatus.FAILED)
        sm.transition_to(SagaInstanceStatus.COMPENSATING)
        sm.transition_to(SagaInstanceStatus.COMPENSATED)
        assert sm.state == SagaInstanceStatus.COMPENSATED

    def test_full_compensation_failed_lifecycle_transitions(self) -> None:
        sm = SagaStateMachine()
        sm.transition_to(SagaInstanceStatus.RUNNING)
        sm.transition_to(SagaInstanceStatus.FAILED)
        sm.transition_to(SagaInstanceStatus.COMPENSATING)
        sm.transition_to(SagaInstanceStatus.COMPENSATION_FAILED)
        assert sm.state == SagaInstanceStatus.COMPENSATION_FAILED

    def test_pending_direct_abort(self) -> None:
        sm = SagaStateMachine()
        sm.transition_to(SagaInstanceStatus.ABORTED)
        assert sm.state == SagaInstanceStatus.ABORTED
