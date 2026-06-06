from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

import pytest

from solocoder_py.workflow import (
    Edge,
    Step,
    StepExecutionContext,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowRepository,
)


class StepTracker:
    def __init__(self) -> None:
        self.executed: List[str] = []
        self.compensated: List[str] = []
        self.outputs: Dict[str, Dict[str, Any]] = {}

    def make_action(
        self, step_id: str, outputs: Dict[str, Any] | None = None, fail: bool = False
    ) -> Callable[[StepExecutionContext], Any]:
        def action(ctx: StepExecutionContext) -> Any:
            self.executed.append(step_id)
            if fail:
                raise RuntimeError(f"Step {step_id} failed intentionally")
            if outputs:
                ctx.outputs.update(outputs)
                self.outputs[step_id] = dict(outputs)
            return None

        return action

    def make_compensation(
        self, step_id: str, fail: bool = False
    ) -> Callable[[StepExecutionContext], Any]:
        def compensation(ctx: StepExecutionContext) -> Any:
            self.compensated.append(step_id)
            if fail:
                raise RuntimeError(f"Compensation for step {step_id} failed intentionally")
            return None

        return compensation


@pytest.fixture
def tracker() -> StepTracker:
    return StepTracker()


@pytest.fixture
def repo() -> WorkflowRepository:
    return WorkflowRepository()


@pytest.fixture
def engine(repo: WorkflowRepository) -> WorkflowEngine:
    return WorkflowEngine(repository=repo)


def make_linear_workflow(
    tracker: StepTracker,
    step_count: int = 3,
    fail_at: int | None = None,
    fail_compensation_at: int | None = None,
) -> Tuple[WorkflowDefinition, List[Step]]:
    steps: List[Step] = []
    for i in range(step_count):
        sid = f"step-{i}"
        should_fail = fail_at is not None and i == fail_at
        comp_should_fail = fail_compensation_at is not None and i == fail_compensation_at
        steps.append(
            Step(
                id=sid,
                name=f"Step {i}",
                action=tracker.make_action(sid, outputs={"value": i}, fail=should_fail),
                compensation=tracker.make_compensation(sid, fail=comp_should_fail),
            )
        )

    edges: List[Edge] = []
    for i in range(step_count - 1):
        edges.append(Edge(from_step_id=f"step-{i}", to_step_id=f"step-{i + 1}"))

    definition = WorkflowDefinition(
        id="wf-linear",
        name="Linear Workflow",
        steps=steps,
        edges=edges,
    )
    return definition, steps


def make_parallel_workflow(
    tracker: StepTracker,
) -> Tuple[WorkflowDefinition, Dict[str, Step]]:
    step_a = Step(
        id="A",
        name="Step A",
        action=tracker.make_action("A", outputs={"a": 1}),
        compensation=tracker.make_compensation("A"),
    )
    step_b = Step(
        id="B",
        name="Step B",
        action=tracker.make_action("B", outputs={"b": 2}),
        compensation=tracker.make_compensation("B"),
    )
    step_c = Step(
        id="C",
        name="Step C",
        action=tracker.make_action("C", outputs={"c": 3}),
        compensation=tracker.make_compensation("C"),
    )
    step_d = Step(
        id="D",
        name="Step D",
        action=tracker.make_action("D", outputs={"d": 4}),
        compensation=tracker.make_compensation("D"),
    )

    steps = {"A": step_a, "B": step_b, "C": step_c, "D": step_d}
    edges = [
        Edge(from_step_id="A", to_step_id="B"),
        Edge(from_step_id="A", to_step_id="C"),
        Edge(from_step_id="B", to_step_id="D"),
        Edge(from_step_id="C", to_step_id="D"),
    ]

    definition = WorkflowDefinition(
        id="wf-parallel",
        name="Parallel Workflow",
        steps=list(steps.values()),
        edges=edges,
    )
    return definition, steps


def make_single_step_workflow(tracker: StepTracker) -> WorkflowDefinition:
    step = Step(
        id="only",
        name="Only Step",
        action=tracker.make_action("only", outputs={"value": 42}),
        compensation=tracker.make_compensation("only"),
    )
    return WorkflowDefinition(
        id="wf-single",
        name="Single Step Workflow",
        steps=[step],
        edges=[],
    )


def make_empty_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="wf-empty",
        name="Empty Workflow",
        steps=[],
        edges=[],
    )
