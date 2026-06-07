from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

import pytest

from solocoder_py.saga import (
    SagaAction,
    SagaCompensation,
    SagaContext,
    SagaDefinition,
    SagaOrchestrator,
    SagaRepository,
    SagaStep,
)


class StepTracker:
    def __init__(self) -> None:
        self.executed: List[str] = []
        self.compensated: List[str] = []
        self.execution_attempts: Dict[str, int] = {}
        self.compensation_attempts: Dict[str, int] = {}
        self.outputs: Dict[str, Dict[str, Any]] = {}

    def make_action(
        self,
        step_id: str,
        outputs: Dict[str, Any] | None = None,
        fail: bool = False,
        fail_n_times: int = 0,
    ) -> SagaAction:
        self.execution_attempts.setdefault(step_id, 0)

        def action(ctx: SagaContext) -> Any:
            self.executed.append(step_id)
            self.execution_attempts[step_id] += 1
            if fail or self.execution_attempts[step_id] <= fail_n_times:
                raise RuntimeError(f"Step {step_id} failed intentionally")
            if outputs:
                ctx.outputs.update(outputs)
                self.outputs[step_id] = dict(outputs)
            return None

        return action

    def make_compensation(
        self,
        step_id: str,
        fail: bool = False,
        fail_n_times: int = 0,
    ) -> SagaCompensation:
        self.compensation_attempts.setdefault(step_id, 0)

        def compensation(ctx: SagaContext) -> Any:
            self.compensated.append(step_id)
            self.compensation_attempts[step_id] += 1
            if fail or self.compensation_attempts[step_id] <= fail_n_times:
                raise RuntimeError(
                    f"Compensation for step {step_id} failed intentionally"
                )
            return None

        return compensation


@pytest.fixture
def tracker() -> StepTracker:
    return StepTracker()


@pytest.fixture
def repo() -> SagaRepository:
    return SagaRepository()


@pytest.fixture
def orchestrator(repo: SagaRepository) -> SagaOrchestrator:
    return SagaOrchestrator(repository=repo)


def make_linear_saga(
    tracker: StepTracker,
    step_count: int = 3,
    fail_at: int | None = None,
    fail_compensation_at: int | None = None,
    action_fail_n_times: Dict[int, int] | None = None,
    compensation_fail_n_times: Dict[int, int] | None = None,
    max_retries: int = 0,
    compensation_max_retries: int = 0,
) -> Tuple[SagaDefinition, List[SagaStep]]:
    action_fail_n_times = action_fail_n_times or {}
    compensation_fail_n_times = compensation_fail_n_times or {}

    steps: List[SagaStep] = []
    for i in range(step_count):
        sid = f"step-{i}"
        should_fail = fail_at is not None and i == fail_at
        comp_should_fail = fail_compensation_at is not None and i == fail_compensation_at
        steps.append(
            SagaStep(
                id=sid,
                name=f"Step {i}",
                action=tracker.make_action(
                    sid,
                    outputs={"value": i},
                    fail=should_fail,
                    fail_n_times=action_fail_n_times.get(i, 0),
                ),
                compensation=tracker.make_compensation(
                    sid,
                    fail=comp_should_fail,
                    fail_n_times=compensation_fail_n_times.get(i, 0),
                ),
                max_retries=max_retries,
                compensation_max_retries=compensation_max_retries,
            )
        )

    definition = SagaDefinition(
        id="saga-linear",
        name="Linear Saga",
        steps=steps,
    )
    return definition, steps


def make_single_step_saga(
    tracker: StepTracker,
    fail: bool = False,
    fail_compensation: bool = False,
    max_retries: int = 0,
    compensation_max_retries: int = 0,
) -> SagaDefinition:
    step = SagaStep(
        id="only",
        name="Only Step",
        action=tracker.make_action("only", outputs={"value": 42}, fail=fail),
        compensation=tracker.make_compensation("only", fail=fail_compensation),
        max_retries=max_retries,
        compensation_max_retries=compensation_max_retries,
    )
    return SagaDefinition(
        id="saga-single",
        name="Single Step Saga",
        steps=[step],
    )


def make_empty_saga() -> SagaDefinition:
    return SagaDefinition(
        id="saga-empty",
        name="Empty Saga",
        steps=[],
    )
