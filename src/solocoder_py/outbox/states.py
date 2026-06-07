from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from .exceptions import InvalidStateTransitionError


class OutboxMessageState(str, Enum):
    PENDING = "待投递"
    DELIVERING = "投递中"
    CONFIRMED = "已确认"
    FAILED = "投递失败"
    DEAD_LETTER = "死信"


_TRANSITIONS: Dict[OutboxMessageState, Set[OutboxMessageState]] = {
    OutboxMessageState.PENDING: {
        OutboxMessageState.DELIVERING,
    },
    OutboxMessageState.DELIVERING: {
        OutboxMessageState.CONFIRMED,
        OutboxMessageState.FAILED,
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
