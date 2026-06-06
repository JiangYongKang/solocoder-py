from __future__ import annotations

import pytest

from solocoder_py.workflow import (
    Edge,
    Step,
    StepCompensationStatus,
    StepExecutionStatus,
    VersionMismatchError,
    WorkflowDefinition,
    WorkflowDefinitionError,
    WorkflowEngine,
    WorkflowExecutionError,
    WorkflowInstanceStatus,
    WorkflowRepository,
)
from tests.workflow.conftest import (
    StepTracker,
    make_empty_workflow,
    make_linear_workflow,
    make_parallel_workflow,
    make_single_step_workflow,
)


class TestWorkflowRepository:
    def test_save_and_find_definition(self, repo: WorkflowRepository) -> None:
        wf = WorkflowDefinition(id="wf1", name="Test")
        repo.save_definition(wf)
        assert repo.find_definition("wf1") is wf
        assert repo.find_definition("missing") is None
        assert repo.count_definitions() == 1

    def test_delete_definition(self, repo: WorkflowRepository) -> None:
        wf = WorkflowDefinition(id="wf1", name="Test")
        repo.save_definition(wf)
        assert repo.delete_definition("wf1") is True
        assert repo.delete_definition("wf1") is False
        assert repo.count_definitions() == 0

    def test_find_unfinished_instances(self, repo: WorkflowRepository, tracker: StepTracker) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=2)
        repo.save_definition(wf_def)

        from solocoder_py.workflow import WorkflowInstance

        pending = WorkflowInstance(id="p1", workflow_id=wf_def.id, workflow_version=wf_def.version)
        completed = WorkflowInstance(id="c1", workflow_id=wf_def.id, workflow_version=wf_def.version)
        completed.start()
        completed.complete()

        repo.save_instance(pending)
        repo.save_instance(completed)

        unfinished = repo.find_unfinished_instances()
        assert len(unfinished) == 1
        assert unfinished[0].id == "p1"

    def test_find_instances_by_workflow(self, repo: WorkflowRepository, tracker: StepTracker) -> None:
        wf1, _ = make_linear_workflow(tracker, step_count=1)
        wf1.id = "wf1"
        wf2, _ = make_linear_workflow(tracker, step_count=1)
        wf2.id = "wf2"
        repo.save_definition(wf1)
        repo.save_definition(wf2)

        from solocoder_py.workflow import WorkflowInstance

        repo.save_instance(WorkflowInstance(id="i1", workflow_id="wf1", workflow_version=1))
        repo.save_instance(WorkflowInstance(id="i2", workflow_id="wf1", workflow_version=1))
        repo.save_instance(WorkflowInstance(id="i3", workflow_id="wf2", workflow_version=1))

        assert len(repo.find_instances_by_workflow("wf1")) == 2
        assert len(repo.find_instances_by_workflow("wf2")) == 1


class TestWorkflowEngineNormalFlow:
    def test_execute_linear_workflow(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=3)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id, inputs={"x": 1})
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPLETED
        assert tracker.executed == ["step-0", "step-1", "step-2"]
        assert tracker.compensated == []
        for i in range(3):
            state = result.get_step_state(f"step-{i}")
            assert state.execution_status == StepExecutionStatus.COMPLETED
            assert state.compensation_status == StepCompensationStatus.NONE

    def test_execute_parallel_workflow(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def, _ = make_parallel_workflow(tracker)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPLETED
        assert "A" in tracker.executed
        assert "D" in tracker.executed
        assert tracker.executed.index("A") < tracker.executed.index("B")
        assert tracker.executed.index("A") < tracker.executed.index("C")
        assert tracker.executed.index("B") < tracker.executed.index("D")
        assert tracker.executed.index("C") < tracker.executed.index("D")

    def test_single_step_workflow(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def = make_single_step_workflow(tracker)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPLETED
        assert tracker.executed == ["only"]
        assert result.get_step_state("only").outputs == {"value": 42}

    def test_empty_workflow(self, engine: WorkflowEngine) -> None:
        wf_def = make_empty_workflow()
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPLETED

    def test_step_without_action_completes_normally(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        step_a = Step(
            id="a",
            name="A with action",
            action=tracker.make_action("a", outputs={"a": 1}),
            compensation=tracker.make_compensation("a"),
        )
        step_b = Step(
            id="b",
            name="B no action",
            compensation=tracker.make_compensation("b"),
        )
        step_c = Step(
            id="c",
            name="C with action",
            action=tracker.make_action("c", outputs={"c": 3}),
            compensation=tracker.make_compensation("c"),
        )
        wf_def = WorkflowDefinition(
            id="wf-no-action",
            name="No Action Step",
            steps=[step_a, step_b, step_c],
            edges=[
                Edge(from_step_id="a", to_step_id="b"),
                Edge(from_step_id="b", to_step_id="c"),
            ],
        )
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPLETED
        assert tracker.executed == ["a", "c"]
        assert result.get_step_state("a").execution_status == StepExecutionStatus.COMPLETED
        assert result.get_step_state("b").execution_status == StepExecutionStatus.COMPLETED
        assert result.get_step_state("c").execution_status == StepExecutionStatus.COMPLETED
        assert result.get_step_state("b").outputs == {}

    def test_step_outputs_preserved(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=2)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.get_step_state("step-0").outputs == {"value": 0}
        assert result.get_step_state("step-1").outputs == {"value": 1}

    def test_create_instance_unknown_workflow_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowDefinitionError, match="Workflow definition not found"):
            engine.create_instance("nonexistent")

    def test_register_duplicate_workflow_raises(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=1)
        engine.register_workflow(wf_def)
        with pytest.raises(WorkflowDefinitionError, match="already exists"):
            engine.register_workflow(wf_def)

    def test_execute_already_completed(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def = make_single_step_workflow(tracker)
        engine.register_workflow(wf_def)
        instance = engine.create_instance(wf_def.id)
        engine.execute(instance.id)
        result = engine.execute(instance.id)
        assert result.status == WorkflowInstanceStatus.COMPLETED

    def test_execute_unknown_instance_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowExecutionError, match="Workflow instance not found"):
            engine.execute("nonexistent")

    def test_get_instance_status(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def = make_single_step_workflow(tracker)
        engine.register_workflow(wf_def)
        instance = engine.create_instance(wf_def.id)
        found = engine.get_instance_status(instance.id)
        assert found is not None
        assert found.id == instance.id
        assert engine.get_instance_status("missing") is None


class TestWorkflowEngineCompensation:
    def test_failure_triggers_compensation_in_reverse_order(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=4, fail_at=2)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPENSATED
        assert tracker.executed == ["step-0", "step-1", "step-2"]
        assert tracker.compensated == ["step-1", "step-0"]

        assert result.get_step_state("step-0").execution_status == StepExecutionStatus.COMPLETED
        assert result.get_step_state("step-0").compensation_status == StepCompensationStatus.COMPLETED
        assert result.get_step_state("step-1").execution_status == StepExecutionStatus.COMPLETED
        assert result.get_step_state("step-1").compensation_status == StepCompensationStatus.COMPLETED
        assert result.get_step_state("step-2").execution_status == StepExecutionStatus.FAILED
        assert result.get_step_state("step-2").compensation_status == StepCompensationStatus.NONE
        assert result.get_step_state("step-3").execution_status == StepExecutionStatus.PENDING

    def test_compensation_failure_continues_and_records(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(
            tracker, step_count=4, fail_at=3, fail_compensation_at=1
        )
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPENSATION_FAILED
        assert tracker.executed == ["step-0", "step-1", "step-2", "step-3"]
        assert tracker.compensated == ["step-2", "step-1", "step-0"]

        assert result.get_step_state("step-1").compensation_status == StepCompensationStatus.FAILED
        assert result.get_step_state("step-1").compensation_error_message is not None
        assert result.get_step_state("step-2").compensation_status == StepCompensationStatus.COMPLETED
        assert result.get_step_state("step-0").compensation_status == StepCompensationStatus.COMPLETED

    def test_no_compensation_action_still_marks_completed(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        step_a = Step(
            id="a",
            name="A",
            action=tracker.make_action("a"),
        )
        step_fail = Step(
            id="b",
            name="B",
            action=tracker.make_action("b", fail=True),
            compensation=tracker.make_compensation("b"),
        )
        wf_def = WorkflowDefinition(
            id="wf1",
            name="No Compensation",
            steps=[step_a, step_fail],
            edges=[Edge(from_step_id="a", to_step_id="b")],
        )
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPENSATED
        assert result.get_step_state("a").compensation_status == StepCompensationStatus.COMPLETED
        assert "a" not in tracker.compensated

    def test_first_step_fails_no_compensation_needed(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=3, fail_at=0)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPENSATED
        assert tracker.executed == ["step-0"]
        assert tracker.compensated == []


class TestWorkflowEngineVersioning:
    def test_version_mismatch_raises(self, engine: WorkflowEngine, tracker: StepTracker) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=2)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)

        wf_def.steps.append(Step(id="new-step", name="New"))
        engine.update_workflow(wf_def)
        assert wf_def.version == 2

        with pytest.raises(VersionMismatchError) as exc_info:
            engine.execute(instance.id)
        assert exc_info.value.expected_version == 1
        assert exc_info.value.actual_version == 2

    def test_version_match_executes_ok(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=2)
        engine.register_workflow(wf_def)
        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)
        assert result.status == WorkflowInstanceStatus.COMPLETED

    def test_update_workflow_increments_version(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=1)
        engine.register_workflow(wf_def)
        assert wf_def.version == 1

        engine.update_workflow(wf_def)
        assert wf_def.version == 2

        engine.update_workflow(wf_def)
        assert wf_def.version == 3

    def test_update_nonexistent_workflow_raises(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=1)
        with pytest.raises(WorkflowDefinitionError, match="not found"):
            engine.update_workflow(wf_def)

    def test_create_instance_uses_current_version(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=1)
        engine.register_workflow(wf_def)

        inst1 = engine.create_instance(wf_def.id)
        assert inst1.workflow_version == 1

        engine.update_workflow(wf_def)
        inst2 = engine.create_instance(wf_def.id)
        assert inst2.workflow_version == 2


class TestWorkflowEngineRecovery:
    def test_resume_unfinished_pending_instance(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def = make_single_step_workflow(tracker)
        engine.register_workflow(wf_def)
        instance = engine.create_instance(wf_def.id)
        assert instance.status == WorkflowInstanceStatus.PENDING

        resumed = engine.resume_unfinished()
        assert len(resumed) == 1
        assert resumed[0].id == instance.id
        assert resumed[0].status == WorkflowInstanceStatus.COMPLETED
        assert tracker.executed == ["only"]

    def test_resume_skips_version_mismatched(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def = make_single_step_workflow(tracker)
        engine.register_workflow(wf_def)
        instance = engine.create_instance(wf_def.id)

        engine.update_workflow(wf_def)

        resumed = engine.resume_unfinished()
        assert len(resumed) == 0
        reloaded = engine.get_instance_status(instance.id)
        assert reloaded is not None
        assert reloaded.status == WorkflowInstanceStatus.PENDING

    def test_resume_skips_compensating_only(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        from solocoder_py.workflow import WorkflowInstance

        wf_def, _ = make_linear_workflow(tracker, step_count=1)
        engine.register_workflow(wf_def)

        compensating = WorkflowInstance(
            id="c1", workflow_id=wf_def.id, workflow_version=wf_def.version
        )
        compensating.start()
        compensating.fail(RuntimeError("test"))
        compensating.start_compensation()
        engine.repository.save_instance(compensating)

        resumed = engine.resume_unfinished()
        assert len(resumed) == 0

    def test_resume_recovers_failed_instance(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        from solocoder_py.workflow import WorkflowInstance

        wf_def, _ = make_linear_workflow(tracker, step_count=3, fail_at=1)
        engine.register_workflow(wf_def)

        failed = WorkflowInstance(
            id="f-recover", workflow_id=wf_def.id, workflow_version=wf_def.version
        )
        failed.start()

        failed.record_step_completed("step-0")
        s0 = failed.get_step_state("step-0")
        s0.mark_running()
        s0.mark_completed(outputs={"value": 0})

        s1 = failed.get_step_state("step-1")
        s1.mark_running()
        original_error = RuntimeError("crashed before compensation started")
        s1.mark_failed(original_error)
        failed.fail(original_error)

        engine.repository.save_instance(failed)

        original_error_type = failed.error_type
        original_error_msg = failed.error_message
        original_error_tb = failed.error_traceback

        resumed = engine.resume_unfinished()
        assert len(resumed) == 1
        assert resumed[0].id == "f-recover"
        assert resumed[0].status == WorkflowInstanceStatus.COMPENSATED

        assert tracker.compensated == ["step-0"]
        assert failed.error_type == original_error_type
        assert failed.error_message == original_error_msg
        assert failed.error_traceback == original_error_tb

        assert failed.get_step_state("step-0").execution_status == StepExecutionStatus.COMPLETED
        assert failed.get_step_state("step-0").compensation_status == StepCompensationStatus.COMPLETED
        assert failed.get_step_state("step-1").execution_status == StepExecutionStatus.FAILED
        assert failed.get_step_state("step-1").compensation_status == StepCompensationStatus.NONE
        assert failed.get_step_state("step-2").execution_status == StepExecutionStatus.PENDING

    def test_failed_records_exception_type_and_traceback(
        self, engine: WorkflowEngine, tracker: StepTracker
    ) -> None:
        wf_def, _ = make_linear_workflow(tracker, step_count=2, fail_at=0)
        engine.register_workflow(wf_def)

        instance = engine.create_instance(wf_def.id)
        result = engine.execute(instance.id)

        assert result.status == WorkflowInstanceStatus.COMPENSATED
        assert result.error_type == "RuntimeError"
        assert result.error_traceback is not None
        assert "RuntimeError" in result.error_traceback

        failed_step = result.get_step_state("step-0")
        assert failed_step.error_type == "RuntimeError"
        assert failed_step.error_traceback is not None

    def test_memory_storage_persists_between_operations(
        self, tracker: StepTracker
    ) -> None:
        shared_repo = WorkflowRepository()
        engine1 = WorkflowEngine(repository=shared_repo)
        wf_def, _ = make_linear_workflow(tracker, step_count=2)
        engine1.register_workflow(wf_def)
        instance = engine1.create_instance(wf_def.id)
        engine1.execute(instance.id)

        engine2 = WorkflowEngine(repository=shared_repo)
        found = engine2.get_instance_status(instance.id)
        assert found is not None
        assert found.status == WorkflowInstanceStatus.COMPLETED
        assert shared_repo.count_instances() == 1
        assert shared_repo.count_definitions() == 1
