from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from .exceptions import InvalidStateTransitionError


class OutboxMessageState(str, Enum):
    PENDING = "pending"
    DELIVERING = "delivering"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


_TRANSITIONS: Dict[OutboxMessageState, Set[OutboxMessageState]] = {
    OutboxMessageState.PENDING: {
        OutboxMessageState.DELIVERING,
        OutboxMessageState.DEAD_LETTER,
    },
    OutboxMessageState.DELIVERING: {
        OutboxMessageState.CONFIRMED,
        OutboxMessageState.FAILED,
        OutboxMessageState.DEAD_LETTER,
    },
    OutboxMessageState.CONFIRMED: set(),
    OutboxMessageState.FAILED: {
        OutboxMessageState.DELIVERING,
        OutboxMessageState.DEAD_LETTER,
    },
    OutboxMessageState.DEAD_LETTER: set(),
}


class OutboxStateMachine:
    def __init__(self, initial_state: OutboxMessageState = OutboxMessageState.PENDING) -> None:
        self._state = initial_state

    @property
    def state(self) -> OutboxMessageState:
        return self._state

    def can_transition_to(self, target: OutboxMessageState) -> bool:
        return target in _TRANSITIONS.get(self._state, set())

    def transition_to(self, target: OutboxMessageState) -> None:
        if not self.can_transition_to(target):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target

    @staticmethod
    def get_valid_transitions(state: OutboxMessageState) -> Set[OutboxMessageState]:
        return _TRANSITIONS.get(state, set()).copy()
