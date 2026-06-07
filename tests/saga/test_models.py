from __future__ import annotations

import pytest

from solocoder_py.saga import (
    SagaDefinition,
    SagaDefinitionError,
    SagaInstance,
    SagaStep,
    SagaStepExecutionState,
    StepCompensationStatus,
    StepExecutionStatus,
)


class TestSagaStep:
    def test_valid_step(self) -> None:
        step = SagaStep(id="s1", name="Step 1")
        assert step.id == "s1"
        assert step.name == "Step 1"
        assert step.action is None
        assert step.compensation is None
        assert step.max_retries == 0
        assert step.compensation_max_retries == 0

    def test_step_with_actions(self) -> None:
        def dummy_action(ctx):
            return None

        def dummy_compensation(ctx):
            return None

        step = SagaStep(
            id="s1",
            name="Step 1",
            action=dummy_action,
            compensation=dummy_compensation,
            max_retries=3,
            compensation_max_retries=2,
        )
        assert step.action is dummy_action
        assert step.compensation is dummy_compensation
        assert step.max_retries == 3
        assert step.compensation_max_retries == 2

    def test_empty_id_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="id cannot be empty"):
            SagaStep(id="", name="Step")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="name cannot be empty"):
            SagaStep(id="s1", name="")

    def test_negative_max_retries_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="max_retries must be >= 0"):
            SagaStep(id="s1", name="Step", max_retries=-1)

    def test_negative_compensation_max_retries_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="compensation_max_retries must be >= 0"):
            SagaStep(id="s1", name="Step", compensation_max_retries=-1)


class TestSagaStepExecutionState:
    def test_initial_state(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        assert state.step_id == "s1"
        assert state.execution_status == StepExecutionStatus.PENDING
        assert state.compensation_status == StepCompensationStatus.NONE
        assert state.execution_attempts == 0
        assert state.compensation_attempts == 0
        assert state.is_execution_completed is False
        assert state.is_compensation_completed is False
        assert state.needs_compensation is False

    def test_mark_execution_running(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_execution_running()
        assert state.execution_status == StepExecutionStatus.RUNNING
        assert state.execution_attempts == 1
        assert state.started_at is not None

    def test_mark_execution_running_increments_attempts(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_execution_running()
        state.mark_execution_running()
        assert state.execution_attempts == 2

    def test_mark_execution_completed(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_execution_completed(outputs={"key": "value"})
        assert state.execution_status == StepExecutionStatus.COMPLETED
        assert state.completed_at is not None
        assert state.outputs == {"key": "value"}
        assert state.is_execution_completed is True

    def test_mark_execution_failed(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        err = RuntimeError("test error")
        state.mark_execution_failed(err)
        assert state.execution_status == StepExecutionStatus.FAILED
        assert state.completed_at is not None
        assert state.error_message == "test error"
        assert state.error_type == "RuntimeError"
        assert state.error_traceback is not None
        assert "RuntimeError" in state.error_traceback

    def test_mark_compensation_pending(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_compensation_pending()
        assert state.compensation_status == StepCompensationStatus.PENDING

    def test_mark_compensation_running(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_compensation_running()
        assert state.compensation_status == StepCompensationStatus.RUNNING
        assert state.compensation_attempts == 1
        assert state.compensation_started_at is not None

    def test_mark_compensation_completed(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_compensation_completed()
        assert state.compensation_status == StepCompensationStatus.COMPLETED
        assert state.compensation_completed_at is not None
        assert state.is_compensation_completed is True

    def test_mark_compensation_failed(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        err = RuntimeError("compensation error")
        state.mark_compensation_failed(err)
        assert state.compensation_status == StepCompensationStatus.FAILED
        assert state.compensation_completed_at is not None
        assert state.compensation_error_message == "compensation error"
        assert state.compensation_error_type == "RuntimeError"
        assert state.compensation_error_traceback is not None

    def test_mark_compensation_skipped(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_compensation_skipped()
        assert state.compensation_status == StepCompensationStatus.SKIPPED

    def test_needs_compensation_after_execution_success(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_execution_completed()
        assert state.needs_compensation is True

    def test_needs_compensation_false_after_compensation_success(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_execution_completed()
        state.mark_compensation_completed()
        assert state.needs_compensation is False

    def test_needs_compensation_true_after_compensation_failed(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        state.mark_execution_completed()
        state.mark_compensation_failed(RuntimeError("fail"))
        assert state.needs_compensation is True

    def test_needs_compensation_false_when_execution_not_completed(self) -> None:
        state = SagaStepExecutionState(step_id="s1")
        assert state.needs_compensation is False
        state.mark_execution_failed(RuntimeError("fail"))
        assert state.needs_compensation is False


class TestSagaDefinition:
    def test_valid_empty_definition(self) -> None:
        saga = SagaDefinition(id="saga-1", name="Test Saga")
        assert saga.id == "saga-1"
        assert saga.name == "Test Saga"
        assert saga.steps == []
        assert saga.step_count() == 0

    def test_valid_definition_with_steps(self) -> None:
        s1 = SagaStep(id="s1", name="Step 1")
        s2 = SagaStep(id="s2", name="Step 2")
        saga = SagaDefinition(id="saga-1", name="Test Saga", steps=[s1, s2])
        assert saga.step_count() == 2
        assert saga.ordered_step_ids() == ["s1", "s2"]

    def test_empty_id_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="id cannot be empty"):
            SagaDefinition(id="", name="Test")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="name cannot be empty"):
            SagaDefinition(id="s1", name="")

    def test_duplicate_step_ids_raises(self) -> None:
        s1 = SagaStep(id="dup", name="Step 1")
        s2 = SagaStep(id="dup", name="Step 2")
        with pytest.raises(SagaDefinitionError, match="Duplicate step id"):
            SagaDefinition(id="saga-1", name="Test", steps=[s1, s2])

    def test_get_step(self) -> None:
        s1 = SagaStep(id="s1", name="Step 1")
        s2 = SagaStep(id="s2", name="Step 2")
        saga = SagaDefinition(id="saga-1", name="Test", steps=[s1, s2])
        assert saga.get_step("s1") is s1
        assert saga.get_step("s2") is s2
        assert saga.get_step("missing") is None


class TestSagaInstance:
    def test_valid_instance(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1", inputs={"x": 1})
        assert inst.id == "inst-1"
        assert inst.saga_id == "saga-1"
        assert inst.inputs == {"x": 1}
        assert inst.status.value == "pending"
        assert inst.is_terminal is False
        assert inst.created_at is not None

    def test_empty_id_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="id cannot be empty"):
            SagaInstance(id="", saga_id="saga-1")

    def test_empty_saga_id_raises(self) -> None:
        with pytest.raises(SagaDefinitionError, match="saga_id cannot be empty"):
            SagaInstance(id="inst-1", saga_id="")

    def test_get_step_state_creates_if_missing(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        state = inst.get_step_state("new-step")
        assert state.step_id == "new-step"
        assert "new-step" in inst.step_states

    def test_get_step_state_returns_existing(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        state1 = inst.get_step_state("s1")
        state2 = inst.get_step_state("s1")
        assert state1 is state2

    def test_lifecycle_transitions(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        inst.start()
        assert inst.status.value == "running"
        assert inst.started_at is not None

        inst.complete()
        assert inst.status.value == "completed"
        assert inst.is_terminal is True
        assert inst.completed_at is not None

    def test_lifecycle_failed_to_compensated(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        inst.start()
        inst.fail(RuntimeError("boom"))
        assert inst.status.value == "failed"
        assert inst.error_message == "boom"
        assert inst.error_type == "RuntimeError"
        assert inst.error_traceback is not None

        inst.start_compensation()
        assert inst.status.value == "compensating"

        inst.complete_compensation(has_failures=False)
        assert inst.status.value == "compensated"
        assert inst.is_terminal is True

    def test_lifecycle_failed_to_compensation_failed(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        inst.start()
        inst.fail(RuntimeError("boom"))
        inst.start_compensation()
        inst.complete_compensation(has_failures=True)
        assert inst.status.value == "compensation_failed"
        assert inst.is_terminal is True

    def test_abort_from_pending(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        inst.abort()
        assert inst.status.value == "aborted"
        assert inst.is_terminal is True

    def test_record_and_get_completed_steps_reversed(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        s0 = inst.get_step_state("s0")
        s0.mark_execution_completed()
        inst.record_step_executed("s0")

        s1 = inst.get_step_state("s1")
        s1.mark_execution_completed()
        inst.record_step_executed("s1")

        s2 = inst.get_step_state("s2")
        s2.mark_execution_failed(RuntimeError("fail"))
        inst.record_step_executed("s2")

        assert inst.get_completed_steps_reversed() == ["s1", "s0"]

    def test_get_execution_trace(self) -> None:
        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        s0 = inst.get_step_state("s0")
        s0.mark_execution_completed(outputs={"v": 1})
        inst.record_step_executed("s0")

        trace = inst.get_execution_trace()
        assert len(trace) == 1
        assert trace[0]["step_id"] == "s0"
        assert trace[0]["outputs"] == {"v": 1}
