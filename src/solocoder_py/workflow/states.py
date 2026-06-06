from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class WorkflowDefinitionError(Exception):
    pass


class WorkflowExecutionError(Exception):
    pass


class VersionMismatchError(Exception):
    def __init__(self, workflow_id: str, expected_version: int, actual_version: int) -> None:
        self.workflow_id = workflow_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Version mismatch for workflow '{workflow_id}': "
            f"instance references version {expected_version}, "
            f"but latest definition is version {actual_version}"
        )


class StepExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepCompensationStatus(str, Enum):
    NONE = "none"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowInstanceStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"


_WORKFLOW_TRANSITIONS: Dict[WorkflowInstanceStatus, Set[WorkflowInstanceStatus]] = {
    WorkflowInstanceStatus.PENDING: {
        WorkflowInstanceStatus.RUNNING,
    },
    WorkflowInstanceStatus.RUNNING: {
        WorkflowInstanceStatus.COMPLETED,
        WorkflowInstanceStatus.FAILED,
    },
    WorkflowInstanceStatus.FAILED: {
        WorkflowInstanceStatus.COMPENSATING,
    },
    WorkflowInstanceStatus.COMPENSATING: {
        WorkflowInstanceStatus.COMPENSATED,
        WorkflowInstanceStatus.COMPENSATION_FAILED,
    },
    WorkflowInstanceStatus.COMPLETED: set(),
    WorkflowInstanceStatus.COMPENSATED: set(),
    WorkflowInstanceStatus.COMPENSATION_FAILED: set(),
}


class WorkflowStateMachine:
    def __init__(self, initial_state: WorkflowInstanceStatus = WorkflowInstanceStatus.PENDING) -> None:
        self._state = initial_state

    @property
    def state(self) -> WorkflowInstanceStatus:
        return self._state

    def can_transition_to(self, target: WorkflowInstanceStatus) -> bool:
        return target in _WORKFLOW_TRANSITIONS.get(self._state, set())

    def transition_to(self, target: WorkflowInstanceStatus) -> None:
        if not self.can_transition_to(target):
            raise WorkflowExecutionError(
                f"Invalid workflow state transition: {self._state.value} -> {target.value}"
            )
        self._state = target
