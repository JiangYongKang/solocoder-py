from __future__ import annotations

import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .states import (
    SagaDefinitionError,
    SagaInstanceStatus,
    SagaStateMachine,
    StepCompensationStatus,
    StepExecutionStatus,
)


SagaAction = Callable[["SagaContext"], Any]
SagaCompensation = Callable[["SagaContext"], Any]


@dataclass
class SagaContext:
    saga_instance_id: str
    step_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    compensation_error: Optional[Exception] = None


@dataclass
class SagaStep:
    id: str
    name: str
    action: Optional[SagaAction] = None
    compensation: Optional[SagaCompensation] = None
    max_retries: int = 0
    compensation_max_retries: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            raise SagaDefinitionError("SagaStep id cannot be empty")
        if not self.name:
            raise SagaDefinitionError("SagaStep name cannot be empty")
        if self.max_retries < 0:
            raise SagaDefinitionError("SagaStep max_retries must be >= 0")
        if self.compensation_max_retries < 0:
            raise SagaDefinitionError("SagaStep compensation_max_retries must be >= 0")


@dataclass
class SagaStepExecutionState:
    step_id: str
    execution_status: StepExecutionStatus = StepExecutionStatus.PENDING
    compensation_status: StepCompensationStatus = StepCompensationStatus.NONE
    execution_attempts: int = 0
    compensation_attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    compensation_started_at: Optional[datetime] = None
    compensation_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    compensation_error_message: Optional[str] = None
    compensation_error_type: Optional[str] = None
    compensation_error_traceback: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)

    def mark_execution_running(self) -> None:
        self.execution_status = StepExecutionStatus.RUNNING
        self.execution_attempts += 1
        if self.started_at is None:
            self.started_at = datetime.now()

    def mark_execution_completed(self, outputs: Optional[Dict[str, Any]] = None) -> None:
        self.execution_status = StepExecutionStatus.COMPLETED
        self.completed_at = datetime.now()
        if outputs:
            self.outputs = outputs

    def mark_execution_failed(self, error: Exception) -> None:
        self.execution_status = StepExecutionStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = str(error)
        self.error_type = type(error).__name__
        self.error_traceback = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def mark_compensation_pending(self) -> None:
        self.compensation_status = StepCompensationStatus.PENDING

    def mark_compensation_running(self) -> None:
        self.compensation_status = StepCompensationStatus.RUNNING
        self.compensation_attempts += 1
        if self.compensation_started_at is None:
            self.compensation_started_at = datetime.now()

    def mark_compensation_completed(self) -> None:
        self.compensation_status = StepCompensationStatus.COMPLETED
        self.compensation_completed_at = datetime.now()

    def mark_compensation_failed(self, error: Exception) -> None:
        self.compensation_status = StepCompensationStatus.FAILED
        self.compensation_completed_at = datetime.now()
        self.compensation_error_message = str(error)
        self.compensation_error_type = type(error).__name__
        self.compensation_error_traceback = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def mark_compensation_skipped(self) -> None:
        self.compensation_status = StepCompensationStatus.SKIPPED

    @property
    def is_execution_completed(self) -> bool:
        return self.execution_status == StepExecutionStatus.COMPLETED

    @property
    def is_compensation_completed(self) -> bool:
        return self.compensation_status == StepCompensationStatus.COMPLETED

    @property
    def needs_compensation(self) -> bool:
        return (
            self.is_execution_completed
            and self.compensation_status
            in {StepCompensationStatus.NONE, StepCompensationStatus.FAILED}
        )


@dataclass
class SagaDefinition:
    id: str
    name: str
    steps: List[SagaStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.id:
            raise SagaDefinitionError("SagaDefinition id cannot be empty")
        if not self.name:
            raise SagaDefinitionError("SagaDefinition name cannot be empty")
        self._validate()

    def _validate(self) -> None:
        step_ids: set[str] = set()
        for step in self.steps:
            if step.id in step_ids:
                raise SagaDefinitionError(f"Duplicate step id: {step.id}")
            step_ids.add(step.id)

    def get_step(self, step_id: str) -> Optional[SagaStep]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def step_count(self) -> int:
        return len(self.steps)

    def ordered_step_ids(self) -> List[str]:
        return [step.id for step in self.steps]


@dataclass
class SagaInstance:
    id: str
    saga_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    step_states: Dict[str, SagaStepExecutionState] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    _state_machine: SagaStateMachine = field(
        default_factory=lambda: SagaStateMachine(SagaInstanceStatus.PENDING)
    )

    def __post_init__(self) -> None:
        if not self.id:
            raise SagaDefinitionError("SagaInstance id cannot be empty")
        if not self.saga_id:
            raise SagaDefinitionError("SagaInstance saga_id cannot be empty")

    @property
    def status(self) -> SagaInstanceStatus:
        return self._state_machine.state

    @property
    def is_terminal(self) -> bool:
        return SagaStateMachine.is_terminal(self.status)

    def get_step_state(self, step_id: str) -> SagaStepExecutionState:
        if step_id not in self.step_states:
            self.step_states[step_id] = SagaStepExecutionState(step_id=step_id)
        return self.step_states[step_id]

    def start(self) -> None:
        self._state_machine.transition_to(SagaInstanceStatus.RUNNING)
        self.started_at = datetime.now()

    def complete(self) -> None:
        self._state_machine.transition_to(SagaInstanceStatus.COMPLETED)
        self.completed_at = datetime.now()

    def fail(self, error: Exception) -> None:
        self._state_machine.transition_to(SagaInstanceStatus.FAILED)
        self.completed_at = datetime.now()
        self.error_message = str(error)
        self.error_type = type(error).__name__
        self.error_traceback = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def start_compensation(self) -> None:
        self._state_machine.transition_to(SagaInstanceStatus.COMPENSATING)

    def complete_compensation(self, has_failures: bool) -> None:
        if has_failures:
            self._state_machine.transition_to(SagaInstanceStatus.COMPENSATION_FAILED)
        else:
            self._state_machine.transition_to(SagaInstanceStatus.COMPENSATED)
        self.completed_at = datetime.now()

    def abort(self) -> None:
        self._state_machine.transition_to(SagaInstanceStatus.ABORTED)
        self.completed_at = datetime.now()

    def record_step_executed(self, step_id: str) -> None:
        if step_id not in self.execution_order:
            self.execution_order.append(step_id)

    def get_completed_steps_reversed(self) -> List[str]:
        result: List[str] = []
        for step_id in reversed(self.execution_order):
            state = self.get_step_state(step_id)
            if state.is_execution_completed:
                result.append(step_id)
        return result

    def get_execution_trace(self) -> List[Dict[str, Any]]:
        trace: List[Dict[str, Any]] = []
        for step_id in self.execution_order:
            state = self.get_step_state(step_id)
            trace.append(
                {
                    "step_id": step_id,
                    "execution_status": state.execution_status.value,
                    "compensation_status": state.compensation_status.value,
                    "execution_attempts": state.execution_attempts,
                    "compensation_attempts": state.compensation_attempts,
                    "outputs": dict(state.outputs),
                    "error": state.error_message,
                    "compensation_error": state.compensation_error_message,
                }
            )
        return trace
