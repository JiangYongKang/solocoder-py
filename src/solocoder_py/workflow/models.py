from __future__ import annotations

import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .states import (
    StepCompensationStatus,
    StepExecutionStatus,
    WorkflowDefinitionError,
    WorkflowInstanceStatus,
    WorkflowStateMachine,
)


StepAction = Callable[["StepExecutionContext"], Any]
CompensationAction = Callable[["StepExecutionContext"], Any]


@dataclass
class StepExecutionContext:
    workflow_instance_id: str
    step_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    compensation_error: Optional[Exception] = None


@dataclass
class Edge:
    from_step_id: str
    to_step_id: str

    def __post_init__(self) -> None:
        if not self.from_step_id:
            raise WorkflowDefinitionError("Edge from_step_id cannot be empty")
        if not self.to_step_id:
            raise WorkflowDefinitionError("Edge to_step_id cannot be empty")
        if self.from_step_id == self.to_step_id:
            raise WorkflowDefinitionError(
                f"Edge cannot reference same step: {self.from_step_id}"
            )


@dataclass
class Step:
    id: str
    name: str
    action: Optional[StepAction] = None
    compensation: Optional[CompensationAction] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise WorkflowDefinitionError("Step id cannot be empty")
        if not self.name:
            raise WorkflowDefinitionError("Step name cannot be empty")


@dataclass
class StepExecutionState:
    step_id: str
    execution_status: StepExecutionStatus = StepExecutionStatus.PENDING
    compensation_status: StepCompensationStatus = StepCompensationStatus.NONE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    compensation_error_message: Optional[str] = None
    compensation_error_type: Optional[str] = None
    compensation_error_traceback: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)

    def mark_running(self) -> None:
        self.execution_status = StepExecutionStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, outputs: Optional[Dict[str, Any]] = None) -> None:
        self.execution_status = StepExecutionStatus.COMPLETED
        self.completed_at = datetime.now()
        if outputs:
            self.outputs = outputs

    def mark_failed(self, error: Exception) -> None:
        self.execution_status = StepExecutionStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = str(error)
        self.error_type = type(error).__name__
        self.error_traceback = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def mark_compensation_running(self) -> None:
        self.compensation_status = StepCompensationStatus.RUNNING

    def mark_compensation_completed(self) -> None:
        self.compensation_status = StepCompensationStatus.COMPLETED

    def mark_compensation_failed(self, error: Exception) -> None:
        self.compensation_status = StepCompensationStatus.FAILED
        self.compensation_error_message = str(error)
        self.compensation_error_type = type(error).__name__
        self.compensation_error_traceback = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )


@dataclass
class WorkflowDefinition:
    id: str
    name: str
    steps: List[Step] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.id:
            raise WorkflowDefinitionError("WorkflowDefinition id cannot be empty")
        if not self.name:
            raise WorkflowDefinitionError("WorkflowDefinition name cannot be empty")
        if self.version < 1:
            raise WorkflowDefinitionError("WorkflowDefinition version must be >= 1")
        self._validate()

    def _validate(self) -> None:
        step_ids: Set[str] = set()
        for step in self.steps:
            if step.id in step_ids:
                raise WorkflowDefinitionError(
                    f"Duplicate step id: {step.id}"
                )
            step_ids.add(step.id)

        for edge in self.edges:
            if edge.from_step_id not in step_ids:
                raise WorkflowDefinitionError(
                    f"Edge references non-existent from_step: {edge.from_step_id}"
                )
            if edge.to_step_id not in step_ids:
                raise WorkflowDefinitionError(
                    f"Edge references non-existent to_step: {edge.to_step_id}"
                )

        self._detect_cycles()

    def _detect_cycles(self) -> None:
        adjacency: Dict[str, List[str]] = {s.id: [] for s in self.steps}
        for edge in self.edges:
            adjacency[edge.from_step_id].append(edge.to_step_id)

        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {s.id: WHITE for s in self.steps}

        def dfs(node: str) -> None:
            color[node] = GRAY
            for neighbor in adjacency[node]:
                if color[neighbor] == GRAY:
                    raise WorkflowDefinitionError(
                        f"Cycle detected involving step: {neighbor}"
                    )
                if color[neighbor] == WHITE:
                    dfs(neighbor)
            color[node] = BLACK

        for step in self.steps:
            if color[step.id] == WHITE:
                dfs(step.id)

    def get_step(self, step_id: str) -> Optional[Step]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_predecessors(self, step_id: str) -> List[str]:
        return [e.from_step_id for e in self.edges if e.to_step_id == step_id]

    def get_successors(self, step_id: str) -> List[str]:
        return [e.to_step_id for e in self.edges if e.from_step_id == step_id]

    def topological_order(self) -> List[str]:
        in_degree: Dict[str, int] = {s.id: 0 for s in self.steps}
        for edge in self.edges:
            in_degree[edge.to_step_id] += 1

        queue: List[str] = [sid for sid, deg in in_degree.items() if deg == 0]
        result: List[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for successor in self.get_successors(node):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)

        return result

    def increment_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now()


@dataclass
class WorkflowInstance:
    id: str
    workflow_id: str
    workflow_version: int
    inputs: Dict[str, Any] = field(default_factory=dict)
    step_states: Dict[str, StepExecutionState] = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    _state_machine: WorkflowStateMachine = field(
        default_factory=lambda: WorkflowStateMachine(WorkflowInstanceStatus.PENDING)
    )

    def __post_init__(self) -> None:
        if not self.id:
            raise WorkflowDefinitionError("WorkflowInstance id cannot be empty")
        if not self.workflow_id:
            raise WorkflowDefinitionError("WorkflowInstance workflow_id cannot be empty")
        if self.workflow_version < 1:
            raise WorkflowDefinitionError("WorkflowInstance workflow_version must be >= 1")

    @property
    def status(self) -> WorkflowInstanceStatus:
        return self._state_machine.state

    def get_step_state(self, step_id: str) -> StepExecutionState:
        if step_id not in self.step_states:
            self.step_states[step_id] = StepExecutionState(step_id=step_id)
        return self.step_states[step_id]

    def start(self) -> None:
        self._state_machine.transition_to(WorkflowInstanceStatus.RUNNING)
        self.started_at = datetime.now()

    def complete(self) -> None:
        self._state_machine.transition_to(WorkflowInstanceStatus.COMPLETED)
        self.completed_at = datetime.now()

    def fail(self, error: Exception) -> None:
        self._state_machine.transition_to(WorkflowInstanceStatus.FAILED)
        self.completed_at = datetime.now()
        self.error_message = str(error)
        self.error_type = type(error).__name__
        self.error_traceback = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def start_compensation(self) -> None:
        self._state_machine.transition_to(WorkflowInstanceStatus.COMPENSATING)

    def complete_compensation(self, has_failures: bool) -> None:
        if has_failures:
            self._state_machine.transition_to(WorkflowInstanceStatus.COMPENSATION_FAILED)
        else:
            self._state_machine.transition_to(WorkflowInstanceStatus.COMPENSATED)
        self.completed_at = datetime.now()

    def record_step_completed(self, step_id: str) -> None:
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)

    def get_completed_steps_reversed(self) -> List[str]:
        return list(reversed(self.completed_steps))
