from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class ParticipantState(str, Enum):
    INITIAL = "INITIAL"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


class InvalidStateTransitionError(Exception):
    def __init__(self, current: ParticipantState, target: ParticipantState) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


_TRANSITIONS: Dict[ParticipantState, Set[ParticipantState]] = {
    ParticipantState.INITIAL: {
        ParticipantState.PREPARED,
        ParticipantState.ABORTED,
    },
    ParticipantState.PREPARED: {
        ParticipantState.COMMITTED,
        ParticipantState.ABORTED,
    },
    ParticipantState.COMMITTED: set(),
    ParticipantState.ABORTED: set(),
}


class ParticipantStateMachine:
    def __init__(self, initial_state: ParticipantState = ParticipantState.INITIAL) -> None:
        self._state = initial_state

    @property
    def state(self) -> ParticipantState:
        return self._state

    def can_transition_to(self, target: ParticipantState) -> bool:
        return target in _TRANSITIONS.get(self._state, set())

    def transition_to(self, target: ParticipantState) -> None:
        if not self.can_transition_to(target):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target

    @staticmethod
    def get_valid_transitions(state: ParticipantState) -> Set[ParticipantState]:
        return _TRANSITIONS.get(state, set()).copy()


class VoteResult(str, Enum):
    YES = "YES"
    NO = "NO"


class CoordinatorDecision(str, Enum):
    COMMIT = "COMMIT"
    ABORT = "ABORT"
