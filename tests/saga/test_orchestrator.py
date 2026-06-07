from __future__ import annotations

import logging
import threading

import pytest

from solocoder_py.saga import (
    IllegalStateTransitionError,
    ResumeResult,
    SagaDefinition,
    SagaDefinitionError,
    SagaExecutionError,
    SagaInstance,
    SagaInstanceStatus,
    SagaOrchestrator,
    SagaRepository,
    SagaStep,
    StepCompensationStatus,
    StepExecutionStatus,
)
from tests.saga.conftest import (
    StepTracker,
    make_empty_saga,
    make_linear_saga,
    make_single_step_saga,
)


class TestSagaRepository:
    def test_save_and_find_definition(self, repo: SagaRepository) -> None:
        saga = make_empty_saga()
        repo.save_definition(saga)
        assert repo.find_definition(saga.id) is saga
        assert repo.find_definition("missing") is None
        assert repo.count_definitions() == 1

    def test_delete_definition(self, repo: SagaRepository) -> None:
        saga = make_empty_saga()
        repo.save_definition(saga)
        assert repo.delete_definition(saga.id) is True
        assert repo.delete_definition(saga.id) is False
        assert repo.count_definitions() == 0

    def test_save_and_find_instance(self, repo: SagaRepository) -> None:
        from solocoder_py.saga import SagaInstance

        inst = SagaInstance(id="inst-1", saga_id="saga-1")
        repo.save_instance(inst)
        assert repo.find_instance("inst-1") is inst
        assert repo.find_instance("missing") is None
        assert repo.count_instances() == 1

    def test_find_unfinished_instances(self, repo: SagaRepository, tracker: StepTracker) -> None:
        saga_def = make_single_step_saga(tracker)
        repo.save_definition(saga_def)

        from solocoder_py.saga import SagaInstance

        pending = SagaInstance(id="p1", saga_id=saga_def.id)
        completed = SagaInstance(id="c1", saga_id=saga_def.id)
        completed.start()
        completed.complete()

        repo.save_instance(pending)
        repo.save_instance(completed)

        unfinished = repo.find_unfinished_instances()
        assert len(unfinished) == 1
        assert unfinished[0].id == "p1"

    def test_clear_all(self, repo: SagaRepository) -> None:
        saga = make_empty_saga()
        repo.save_definition(saga)
        from solocoder_py.saga import SagaInstance

        repo.save_instance(SagaInstance(id="i1", saga_id=saga.id))
        assert repo.count_definitions() == 1
        assert repo.count_instances() == 1
        repo.clear_all()
        assert repo.count_definitions() == 0
        assert repo.count_instances() == 0


class TestSagaOrchestratorNormalFlow:
    def test_execute_linear_saga_all_success(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(tracker, step_count=3)
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id, inputs={"x": 1})
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPLETED
        assert tracker.executed == ["step-0", "step-1", "step-2"]
        assert tracker.compensated == []
        for i in range(3):
            state = result.get_step_state(f"step-{i}")
            assert state.execution_status == StepExecutionStatus.COMPLETED
            assert state.compensation_status == StepCompensationStatus.NONE
            assert state.outputs == {"value": i}

    def test_execute_single_step_saga(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPLETED
        assert tracker.executed == ["only"]
        assert result.get_step_state("only").outputs == {"value": 42}

    def test_execute_empty_saga(self, orchestrator: SagaOrchestrator) -> None:
        saga_def = make_empty_saga()
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPLETED

    def test_execute_already_completed_returns_same(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)
        result1 = orchestrator.execute(instance.id)
        assert result1.status == SagaInstanceStatus.COMPLETED
        tracker.executed.clear()

        result2 = orchestrator.execute(instance.id)
        assert result2.status == SagaInstanceStatus.COMPLETED
        assert tracker.executed == []

    def test_register_duplicate_saga_raises(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        with pytest.raises(SagaDefinitionError, match="already exists"):
            orchestrator.register_saga(saga_def)

    def test_create_instance_unknown_saga_raises(
        self, orchestrator: SagaOrchestrator
    ) -> None:
        with pytest.raises(SagaDefinitionError, match="not found"):
            orchestrator.create_instance("nonexistent")

    def test_execute_unknown_instance_raises(
        self, orchestrator: SagaOrchestrator
    ) -> None:
        with pytest.raises(SagaExecutionError, match="not found"):
            orchestrator.execute("nonexistent")

    def test_get_instance(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)
        found = orchestrator.get_instance(instance.id)
        assert found is not None
        assert found.id == instance.id
        assert orchestrator.get_instance("missing") is None


class TestSagaOrchestratorCompensation:
    def test_failure_triggers_reverse_compensation(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(tracker, step_count=4, fail_at=2)
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPENSATED
        assert tracker.executed == ["step-0", "step-1", "step-2"]
        assert tracker.compensated == ["step-1", "step-0"]

        assert result.get_step_state("step-0").execution_status == StepExecutionStatus.COMPLETED
        assert result.get_step_state("step-0").compensation_status == StepCompensationStatus.COMPLETED
        assert result.get_step_state("step-1").execution_status == StepExecutionStatus.COMPLETED
        assert result.get_step_state("step-1").compensation_status == StepCompensationStatus.COMPLETED
        assert result.get_step_state("step-2").execution_status == StepExecutionStatus.FAILED
        assert result.get_step_state("step-2").compensation_status == StepCompensationStatus.NONE
        assert result.get_step_state("step-3").execution_status == StepExecutionStatus.PENDING

    def test_compensation_idempotent_on_repeated_call(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(tracker, step_count=3, fail_at=1)
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result1 = orchestrator.execute(instance.id)
        assert result1.status == SagaInstanceStatus.COMPENSATED
        assert tracker.compensated == ["step-0"]
        tracker.compensated.clear()

        result2 = orchestrator.compensate(instance.id)
        assert result2.status == SagaInstanceStatus.COMPENSATED
        assert tracker.compensated == []

    def test_compensation_failure_records_and_continues(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(
            tracker, step_count=4, fail_at=3, fail_compensation_at=1
        )
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPENSATION_FAILED
        assert tracker.executed == ["step-0", "step-1", "step-2", "step-3"]
        assert tracker.compensated == ["step-2", "step-1", "step-0"]

        assert result.get_step_state("step-1").compensation_status == StepCompensationStatus.FAILED
        assert result.get_step_state("step-1").compensation_error_message is not None
        assert result.get_step_state("step-2").compensation_status == StepCompensationStatus.COMPLETED
        assert result.get_step_state("step-0").compensation_status == StepCompensationStatus.COMPLETED

    def test_no_compensation_action_marks_completed(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        step_a = SagaStep(
            id="a",
            name="A",
            action=tracker.make_action("a"),
        )
        step_fail = SagaStep(
            id="b",
            name="B",
            action=tracker.make_action("b", fail=True),
            compensation=tracker.make_compensation("b"),
        )
        saga_def = SagaDefinition(
            id="saga-no-comp",
            name="No Compensation Action",
            steps=[step_a, step_fail],
        )
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPENSATED
        assert result.get_step_state("a").compensation_status == StepCompensationStatus.COMPLETED
        assert "a" not in tracker.compensated

    def test_first_step_fails_no_compensation_needed(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(tracker, step_count=3, fail_at=0)
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPENSATED
        assert tracker.executed == ["step-0"]
        assert tracker.compensated == []

    def test_compensate_pending_instance_aborts(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)

        result = orchestrator.compensate(instance.id)
        assert result.status == SagaInstanceStatus.ABORTED
        assert tracker.executed == []
        assert tracker.compensated == []

    def test_compensate_completed_instance_raises(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)
        orchestrator.execute(instance.id)

        with pytest.raises(SagaExecutionError, match="successfully completed"):
            orchestrator.compensate(instance.id)

    def test_compensate_already_compensated_returns_same(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(tracker, step_count=2, fail_at=1)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)
        result1 = orchestrator.execute(instance.id)
        assert result1.status == SagaInstanceStatus.COMPENSATED
        tracker.compensated.clear()

        result2 = orchestrator.compensate(instance.id)
        assert result2.status == SagaInstanceStatus.COMPENSATED
        assert tracker.compensated == []

    def test_execute_compensating_state_continues_compensation(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        from solocoder_py.saga import SagaInstance

        saga_def, _ = make_linear_saga(tracker, step_count=3, fail_at=2)
        orchestrator.register_saga(saga_def)

        inst = SagaInstance(id="mid-comp", saga_id=saga_def.id)
        inst.start()

        s0 = inst.get_step_state("step-0")
        s0.mark_execution_completed(outputs={"value": 0})
        inst.record_step_executed("step-0")

        s1 = inst.get_step_state("step-1")
        s1.mark_execution_completed(outputs={"value": 1})
        inst.record_step_executed("step-1")

        s2 = inst.get_step_state("step-2")
        s2.mark_execution_failed(RuntimeError("crashed"))
        inst.record_step_executed("step-2")
        inst.fail(RuntimeError("crashed"))
        inst.start_compensation()

        orchestrator.repository.save_instance(inst)

        result = orchestrator.execute(inst.id)
        assert result.status == SagaInstanceStatus.COMPENSATED
        assert tracker.compensated == ["step-1", "step-0"]


class TestSagaOrchestratorRetry:
    def test_action_retries_on_failure_then_succeeds(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = SagaDefinition(
            id="saga-retry-success",
            name="Retry Success",
            steps=[
                SagaStep(
                    id="retry-step",
                    name="Retry Step",
                    action=tracker.make_action("retry-step", outputs={"ok": True}, fail_n_times=2),
                    compensation=tracker.make_compensation("retry-step"),
                    max_retries=3,
                )
            ],
        )
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPLETED
        assert tracker.executed == ["retry-step", "retry-step", "retry-step"]
        assert tracker.execution_attempts["retry-step"] == 3
        assert result.get_step_state("retry-step").execution_status == StepExecutionStatus.COMPLETED

    def test_action_retries_exhausted_triggers_compensation(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(
            tracker,
            step_count=3,
            fail_at=1,
            max_retries=2,
            compensation_max_retries=0,
        )
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPENSATED
        assert tracker.execution_attempts["step-1"] == 3
        assert tracker.compensated == ["step-0"]

    def test_compensation_retries_then_succeeds(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = SagaDefinition(
            id="saga-comp-retry",
            name="Comp Retry",
            steps=[
                SagaStep(
                    id="s1",
                    name="Step 1",
                    action=tracker.make_action("s1", outputs={"v": 1}),
                    compensation=tracker.make_compensation("s1", fail_n_times=1),
                    compensation_max_retries=2,
                ),
                SagaStep(
                    id="s2",
                    name="Step 2",
                    action=tracker.make_action("s2", fail=True),
                    compensation=tracker.make_compensation("s2"),
                ),
            ],
        )
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPENSATED
        assert tracker.compensation_attempts["s1"] == 2
        assert result.get_step_state("s1").compensation_status == StepCompensationStatus.COMPLETED

    def test_compensation_retries_exhausted_marks_failed(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(
            tracker,
            step_count=3,
            fail_at=2,
            fail_compensation_at=0,
            compensation_max_retries=1,
        )
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        assert result.status == SagaInstanceStatus.COMPENSATION_FAILED
        assert tracker.compensation_attempts["step-0"] == 2
        assert result.get_step_state("step-0").compensation_status == StepCompensationStatus.FAILED


class TestSagaOrchestratorAbort:
    def test_abort_pending_instance(self, orchestrator: SagaOrchestrator, tracker: StepTracker) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)

        result = orchestrator.abort(instance.id)
        assert result.status == SagaInstanceStatus.ABORTED

    def test_abort_running_instance_triggers_compensation(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        from solocoder_py.saga import SagaInstance

        saga_def, _ = make_linear_saga(tracker, step_count=3)
        orchestrator.register_saga(saga_def)

        inst = SagaInstance(id="abort-me", saga_id=saga_def.id)
        inst.start()
        s0 = inst.get_step_state("step-0")
        s0.mark_execution_completed(outputs={"value": 0})
        inst.record_step_executed("step-0")
        orchestrator.repository.save_instance(inst)

        result = orchestrator.abort(inst.id)
        assert result.status in {SagaInstanceStatus.COMPENSATED, SagaInstanceStatus.ABORTED}
        assert tracker.compensated == ["step-0"]

    def test_abort_terminal_instance_noop(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)
        orchestrator.execute(instance.id)

        result = orchestrator.abort(instance.id)
        assert result.status == SagaInstanceStatus.COMPLETED


class TestSagaOrchestratorIllegalTransitions:
    def test_execute_aborted_instance_raises(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)
        orchestrator.abort(instance.id)

        with pytest.raises(SagaExecutionError, match="Cannot execute saga instance"):
            orchestrator.execute(instance.id)


class TestSagaOrchestratorResume:
    def test_resume_unfinished_pending_instance(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instance = orchestrator.create_instance(saga_def.id)
        assert instance.status == SagaInstanceStatus.PENDING

        resumed = orchestrator.resume_unfinished()
        assert len(resumed) == 1
        assert resumed[0].id == instance.id
        assert resumed[0].status == SagaInstanceStatus.COMPLETED
        assert tracker.executed == ["only"]

    def test_resume_recovers_failed_instance(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        from solocoder_py.saga import SagaInstance

        saga_def, _ = make_linear_saga(tracker, step_count=3, fail_at=1)
        orchestrator.register_saga(saga_def)

        failed = SagaInstance(id="f-recover", saga_id=saga_def.id)
        failed.start()

        failed.record_step_executed("step-0")
        s0 = failed.get_step_state("step-0")
        s0.mark_running() if hasattr(s0, "mark_running") else s0.mark_execution_running()
        s0.mark_execution_completed(outputs={"value": 0})

        s1 = failed.get_step_state("step-1")
        s1.mark_execution_failed(RuntimeError("crashed"))
        failed.record_step_executed("step-1")
        failed.fail(RuntimeError("crashed"))

        orchestrator.repository.save_instance(failed)

        resumed = orchestrator.resume_unfinished()
        assert len(resumed) == 1
        assert resumed[0].id == "f-recover"
        assert resumed[0].status == SagaInstanceStatus.COMPENSATED
        assert tracker.compensated == ["step-0"]


class TestSagaOrchestratorExecutionTrace:
    def test_execution_trace_available(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def, _ = make_linear_saga(tracker, step_count=3, fail_at=1)
        orchestrator.register_saga(saga_def)

        instance = orchestrator.create_instance(saga_def.id)
        result = orchestrator.execute(instance.id)

        trace = result.get_execution_trace()
        assert len(trace) == 2
        assert trace[0]["step_id"] == "step-0"
        assert trace[0]["execution_status"] == "completed"
        assert trace[0]["compensation_status"] == "completed"
        assert trace[1]["step_id"] == "step-1"
        assert trace[1]["execution_status"] == "failed"
        assert trace[1]["compensation_status"] == "none"
        assert trace[1]["error"] is not None


class TestResumeResult:
    def test_empty_result(self) -> None:
        result = ResumeResult()
        assert len(result) == 0
        assert bool(result) is False
        assert result.total_attempted == 0
        assert result.has_failures is False
        assert list(result) == []

    def test_result_with_succeeded(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        inst = orchestrator.create_instance(saga_def.id)

        result = ResumeResult(succeeded=[inst])
        assert len(result) == 1
        assert bool(result) is True
        assert result[0] is inst
        assert result.total_attempted == 1
        assert result.has_failures is False
        assert list(result) == [inst]

    def test_result_with_failures(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        inst1 = orchestrator.create_instance(saga_def.id)
        inst2 = orchestrator.create_instance(saga_def.id)
        err = RuntimeError("boom")

        result = ResumeResult(succeeded=[inst1], failed=[(inst2, err)])
        assert len(result) == 1
        assert result.total_attempted == 2
        assert result.has_failures is True
        assert result.failed[0][0] is inst2
        assert result.failed[0][1] is err

    def test_result_iteration(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        inst1 = orchestrator.create_instance(saga_def.id)
        inst2 = orchestrator.create_instance(saga_def.id)

        result = ResumeResult(succeeded=[inst1, inst2])
        collected = [x for x in result]
        assert collected == [inst1, inst2]


class TestResumeUnfinishedFailures:
    def test_resume_records_failures(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker, caplog: pytest.LogCaptureFixture
    ) -> None:
        from solocoder_py.saga import SagaInstance as SI
        from solocoder_py.saga import SagaStateMachine

        saga_def, _ = make_linear_saga(tracker, step_count=2)
        orchestrator.register_saga(saga_def)

        ok_inst = orchestrator.create_instance(saga_def.id)

        weird_inst = SI(
            id="weird-instance",
            saga_id="nonexistent-saga",
        )
        weird_inst.start()
        orchestrator.repository.save_instance(weird_inst)

        with caplog.at_level(logging.WARNING, logger="solocoder_py.saga.orchestrator"):
            result = orchestrator.resume_unfinished()

        assert result.total_attempted == 2
        assert len(result.succeeded) == 1
        assert result.succeeded[0].id == ok_inst.id
        assert len(result.failed) == 1
        assert result.failed[0][0].id == "weird-instance"
        assert isinstance(result.failed[0][1], SagaDefinitionError)

        assert any(
            "weird-instance" in rec.message
            for rec in caplog.records
        )

    def test_resume_no_unfinished_returns_empty(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)

        result = orchestrator.resume_unfinished()
        assert len(result) == 0
        assert result.total_attempted == 0
        assert result.has_failures is False

    def test_resume_all_succeed(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        orchestrator.create_instance(saga_def.id)
        orchestrator.create_instance(saga_def.id)

        result = orchestrator.resume_unfinished()
        assert len(result) == 2
        assert result.total_attempted == 2
        assert result.has_failures is False
        for inst in result:
            assert inst.status == SagaInstanceStatus.COMPLETED


class TestConcurrencySafety:
    def test_repository_concurrent_save_definitions(self, repo: SagaRepository) -> None:
        errors: list[Exception] = []

        def save_def(idx: int) -> None:
            try:
                saga = SagaDefinition(
                    id=f"saga-{idx}",
                    name=f"Saga {idx}",
                    steps=[
                        SagaStep(id=f"s{idx}-0", name=f"Step 0 of {idx}"),
                    ],
                )
                repo.save_definition(saga)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_def, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert repo.count_definitions() == 50

    def test_repository_concurrent_save_instances(self, repo: SagaRepository) -> None:
        errors: list[Exception] = []

        def save_inst(idx: int) -> None:
            try:
                inst = SagaInstance(id=f"inst-{idx}", saga_id="shared-saga")
                repo.save_instance(inst)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=save_inst, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert repo.count_instances() == 50

    def test_orchestrator_concurrent_create_instances(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        created: list[SagaInstance] = []
        lock = threading.Lock()
        errors: list[Exception] = []

        def create() -> None:
            try:
                inst = orchestrator.create_instance(saga_def.id, inputs={"x": 1})
                with lock:
                    created.append(inst)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(created) == 30
        assert orchestrator.repository.count_instances() == 30

    def test_orchestrator_concurrent_execute(
        self, orchestrator: SagaOrchestrator, tracker: StepTracker
    ) -> None:
        saga_def = make_single_step_saga(tracker)
        orchestrator.register_saga(saga_def)
        instances = [
            orchestrator.create_instance(saga_def.id) for _ in range(20)
        ]
        errors: list[Exception] = []

        def execute_inst(inst: SagaInstance) -> None:
            try:
                orchestrator.execute(inst.id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=execute_inst, args=(inst,)) for inst in instances]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for inst in instances:
            reloaded = orchestrator.get_instance(inst.id)
            assert reloaded is not None
            assert reloaded.status == SagaInstanceStatus.COMPLETED

    def test_orchestrator_concurrent_register_duplicate_is_safe(
        self, orchestrator: SagaOrchestrator
    ) -> None:
        saga_def = SagaDefinition(
            id="unique-saga",
            name="Unique",
            steps=[SagaStep(id="s0", name="S0")],
        )

        errors: list[Exception] = []

        def register() -> None:
            try:
                orchestrator.register_saga(saga_def)
            except SagaDefinitionError:
                pass
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert orchestrator.repository.count_definitions() == 1
