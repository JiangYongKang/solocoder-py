from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class SagaDefinitionError(Exception):
    pass


class SagaExecutionError(Exception):
    pass


class IllegalStateTransitionError(SagaExecutionError):
    def __init__(self, current: "SagaInstanceStatus", target: "SagaInstanceStatus") -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Illegal saga state transition: {current.value} -> {target.value}"
        )


class StepExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepCompensationStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SagaInstanceStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"
    ABORTED = "aborted"


_SAGA_TRANSITIONS: Dict[SagaInstanceStatus, Set[SagaInstanceStatus]] = {
    SagaInstanceStatus.PENDING: {
        SagaInstanceStatus.RUNNING,
        SagaInstanceStatus.ABORTED,
    },
    SagaInstanceStatus.RUNNING: {
        SagaInstanceStatus.COMPLETED,
        SagaInstanceStatus.FAILED,
        SagaInstanceStatus.ABORTED,
    },
    SagaInstanceStatus.FAILED: {
        SagaInstanceStatus.COMPENSATING,
    },
    SagaInstanceStatus.COMPENSATING: {
        SagaInstanceStatus.COMPENSATED,
        SagaInstanceStatus.COMPENSATION_FAILED,
    },
    SagaInstanceStatus.COMPLETED: set(),
    SagaInstanceStatus.COMPENSATED: set(),
    SagaInstanceStatus.COMPENSATION_FAILED: set(),
    SagaInstanceStatus.ABORTED: set(),
}


class SagaStateMachine:
    def __init__(self, initial_state: SagaInstanceStatus = SagaInstanceStatus.PENDING) -> None:
        self._state = initial_state

    @property
    def state(self) -> SagaInstanceStatus:
        return self._state

    def can_transition_to(self, target: SagaInstanceStatus) -> bool:
        return target in _SAGA_TRANSITIONS.get(self._state, set())

    def transition_to(self, target: SagaInstanceStatus) -> None:
        if not self.can_transition_to(target):
            raise IllegalStateTransitionError(self._state, target)
        self._state = target

    @staticmethod
    def is_terminal(status: SagaInstanceStatus) -> bool:
        return status in {
            SagaInstanceStatus.COMPLETED,
            SagaInstanceStatus.COMPENSATED,
            SagaInstanceStatus.COMPENSATION_FAILED,
            SagaInstanceStatus.ABORTED,
        }
