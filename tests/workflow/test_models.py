from __future__ import annotations

import pytest

from solocoder_py.workflow import (
    Edge,
    Step,
    StepCompensationStatus,
    StepExecutionStatus,
    WorkflowDefinition,
    WorkflowDefinitionError,
    WorkflowInstance,
    WorkflowInstanceStatus,
)
from tests.workflow.conftest import StepTracker


class TestStep:
    def test_create_step_success(self) -> None:
        step = Step(id="s1", name="Step One")
        assert step.id == "s1"
        assert step.name == "Step One"
        assert step.action is None
        assert step.compensation is None

    def test_step_empty_id_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="Step id cannot be empty"):
            Step(id="", name="Test")

    def test_step_empty_name_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="Step name cannot be empty"):
            Step(id="s1", name="")


class TestEdge:
    def test_create_edge_success(self) -> None:
        edge = Edge(from_step_id="a", to_step_id="b")
        assert edge.from_step_id == "a"
        assert edge.to_step_id == "b"

    def test_edge_empty_from_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="Edge from_step_id cannot be empty"):
            Edge(from_step_id="", to_step_id="b")

    def test_edge_empty_to_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="Edge to_step_id cannot be empty"):
            Edge(from_step_id="a", to_step_id="")

    def test_edge_self_reference_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="Edge cannot reference same step"):
            Edge(from_step_id="a", to_step_id="a")


class TestWorkflowDefinition:
    def test_empty_workflow(self) -> None:
        wf = WorkflowDefinition(id="wf1", name="Empty")
        assert wf.id == "wf1"
        assert wf.name == "Empty"
        assert wf.steps == []
        assert wf.edges == []
        assert wf.version == 1
        assert wf.topological_order() == []

    def test_duplicate_step_ids_raise(self) -> None:
        steps = [Step(id="a", name="A1"), Step(id="a", name="A2")]
        with pytest.raises(WorkflowDefinitionError, match="Duplicate step id"):
            WorkflowDefinition(id="wf1", name="Test", steps=steps)

    def test_edge_unknown_from_step_raises(self) -> None:
        steps = [Step(id="a", name="A")]
        edges = [Edge(from_step_id="unknown", to_step_id="a")]
        with pytest.raises(WorkflowDefinitionError, match="non-existent from_step"):
            WorkflowDefinition(id="wf1", name="Test", steps=steps, edges=edges)

    def test_edge_unknown_to_step_raises(self) -> None:
        steps = [Step(id="a", name="A")]
        edges = [Edge(from_step_id="a", to_step_id="unknown")]
        with pytest.raises(WorkflowDefinitionError, match="non-existent to_step"):
            WorkflowDefinition(id="wf1", name="Test", steps=steps, edges=edges)

    def test_cycle_detection(self) -> None:
        steps = [Step(id="a", name="A"), Step(id="b", name="B")]
        edges = [Edge(from_step_id="a", to_step_id="b"), Edge(from_step_id="b", to_step_id="a")]
        with pytest.raises(WorkflowDefinitionError, match="Cycle detected"):
            WorkflowDefinition(id="wf1", name="Test", steps=steps, edges=edges)

    def test_three_node_cycle(self) -> None:
        steps = [Step(id="a", name="A"), Step(id="b", name="B"), Step(id="c", name="C")]
        edges = [
            Edge(from_step_id="a", to_step_id="b"),
            Edge(from_step_id="b", to_step_id="c"),
            Edge(from_step_id="c", to_step_id="a"),
        ]
        with pytest.raises(WorkflowDefinitionError, match="Cycle detected"):
            WorkflowDefinition(id="wf1", name="Test", steps=steps, edges=edges)

    def test_topological_order_linear(self) -> None:
        steps = [Step(id="a", name="A"), Step(id="b", name="B"), Step(id="c", name="C")]
        edges = [Edge(from_step_id="a", to_step_id="b"), Edge(from_step_id="b", to_step_id="c")]
        wf = WorkflowDefinition(id="wf1", name="Linear", steps=steps, edges=edges)
        assert wf.topological_order() == ["a", "b", "c"]

    def test_topological_order_parallel(self) -> None:
        steps = [
            Step(id="A", name="A"),
            Step(id="B", name="B"),
            Step(id="C", name="C"),
            Step(id="D", name="D"),
        ]
        edges = [
            Edge(from_step_id="A", to_step_id="B"),
            Edge(from_step_id="A", to_step_id="C"),
            Edge(from_step_id="B", to_step_id="D"),
            Edge(from_step_id="C", to_step_id="D"),
        ]
        wf = WorkflowDefinition(id="wf1", name="Parallel", steps=steps, edges=edges)
        order = wf.topological_order()
        assert order[0] == "A"
        assert order[-1] == "D"
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_get_step(self) -> None:
        step = Step(id="a", name="A")
        wf = WorkflowDefinition(id="wf1", name="Test", steps=[step])
        assert wf.get_step("a") is step
        assert wf.get_step("missing") is None

    def test_get_predecessors_and_successors(self) -> None:
        steps = [Step(id="a", name="A"), Step(id="b", name="B"), Step(id="c", name="C")]
        edges = [Edge(from_step_id="a", to_step_id="b"), Edge(from_step_id="b", to_step_id="c")]
        wf = WorkflowDefinition(id="wf1", name="Test", steps=steps, edges=edges)
        assert wf.get_predecessors("a") == []
        assert wf.get_predecessors("b") == ["a"]
        assert wf.get_predecessors("c") == ["b"]
        assert wf.get_successors("a") == ["b"]
        assert wf.get_successors("b") == ["c"]
        assert wf.get_successors("c") == []

    def test_increment_version(self) -> None:
        wf = WorkflowDefinition(id="wf1", name="Test")
        assert wf.version == 1
        wf.increment_version()
        assert wf.version == 2
        wf.increment_version()
        assert wf.version == 3

    def test_empty_id_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="WorkflowDefinition id cannot be empty"):
            WorkflowDefinition(id="", name="Test")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="WorkflowDefinition name cannot be empty"):
            WorkflowDefinition(id="wf1", name="")

    def test_version_less_than_one_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="version must be >= 1"):
            WorkflowDefinition(id="wf1", name="Test", version=0)


class TestWorkflowInstance:
    def test_create_instance(self) -> None:
        inst = WorkflowInstance(id="inst1", workflow_id="wf1", workflow_version=1)
        assert inst.id == "inst1"
        assert inst.workflow_id == "wf1"
        assert inst.workflow_version == 1
        assert inst.status == WorkflowInstanceStatus.PENDING
        assert inst.completed_steps == []

    def test_state_transitions_normal(self) -> None:
        inst = WorkflowInstance(id="inst1", workflow_id="wf1", workflow_version=1)
        assert inst.status == WorkflowInstanceStatus.PENDING
        inst.start()
        assert inst.status == WorkflowInstanceStatus.RUNNING
        inst.complete()
        assert inst.status == WorkflowInstanceStatus.COMPLETED

    def test_state_transitions_with_compensation(self) -> None:
        inst = WorkflowInstance(id="inst1", workflow_id="wf1", workflow_version=1)
        inst.start()
        inst.fail(RuntimeError("oops"))
        assert inst.status == WorkflowInstanceStatus.FAILED
        assert inst.error_message == "oops"
        assert inst.error_type == "RuntimeError"
        assert inst.error_traceback is not None
        assert "RuntimeError" in inst.error_traceback
        inst.start_compensation()
        assert inst.status == WorkflowInstanceStatus.COMPENSATING
        inst.complete_compensation(has_failures=False)
        assert inst.status == WorkflowInstanceStatus.COMPENSATED

    def test_step_execution_state_error_details(self) -> None:
        from solocoder_py.workflow import StepExecutionState

        state = StepExecutionState(step_id="s1")
        try:
            raise ValueError("something wrong")
        except ValueError as exc:
            state.mark_failed(exc)
        assert state.error_message == "something wrong"
        assert state.error_type == "ValueError"
        assert state.error_traceback is not None
        assert "ValueError" in state.error_traceback

    def test_step_execution_state_compensation_error_details(self) -> None:
        from solocoder_py.workflow import StepExecutionState

        state = StepExecutionState(step_id="s1")
        try:
            raise TypeError("compensation broken")
        except TypeError as exc:
            state.mark_compensation_failed(exc)
        assert state.compensation_error_message == "compensation broken"
        assert state.compensation_error_type == "TypeError"
        assert state.compensation_error_traceback is not None
        assert "TypeError" in state.compensation_error_traceback

    def test_compensation_with_failures(self) -> None:
        inst = WorkflowInstance(id="inst1", workflow_id="wf1", workflow_version=1)
        inst.start()
        inst.fail(RuntimeError("oops"))
        inst.start_compensation()
        inst.complete_compensation(has_failures=True)
        assert inst.status == WorkflowInstanceStatus.COMPENSATION_FAILED

    def test_get_step_state_creates_if_missing(self) -> None:
        inst = WorkflowInstance(id="inst1", workflow_id="wf1", workflow_version=1)
        state = inst.get_step_state("s1")
        assert state.step_id == "s1"
        assert state.execution_status == StepExecutionStatus.PENDING
        assert state.compensation_status == StepCompensationStatus.NONE

    def test_record_completed_steps(self) -> None:
        inst = WorkflowInstance(id="inst1", workflow_id="wf1", workflow_version=1)
        inst.record_step_completed("a")
        inst.record_step_completed("b")
        inst.record_step_completed("a")
        assert inst.completed_steps == ["a", "b"]
        assert inst.get_completed_steps_reversed() == ["b", "a"]

    def test_empty_id_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="WorkflowInstance id cannot be empty"):
            WorkflowInstance(id="", workflow_id="wf1", workflow_version=1)

    def test_empty_workflow_id_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="WorkflowInstance workflow_id cannot be empty"):
            WorkflowInstance(id="inst1", workflow_id="", workflow_version=1)

    def test_version_less_than_one_raises(self) -> None:
        with pytest.raises(WorkflowDefinitionError, match="workflow_version must be >= 1"):
            WorkflowInstance(id="inst1", workflow_id="wf1", workflow_version=0)
