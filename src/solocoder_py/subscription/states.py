from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class InvalidStateTransitionError(Exception):
    def __init__(self, current: "SubscriptionState", target: "SubscriptionState") -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


class SubscriptionState(str, Enum):
    TRIAL = "试用"
    ACTIVE = "活跃"
    PAUSED = "暂停"
    DOWNGRADE_PENDING = "降级处理中"
    CANCELLED = "已取消"
    EXPIRED = "已过期"


_TRANSITIONS: Dict[SubscriptionState, Set[SubscriptionState]] = {
    SubscriptionState.TRIAL: {
        SubscriptionState.ACTIVE,
        SubscriptionState.CANCELLED,
        SubscriptionState.EXPIRED,
    },
    SubscriptionState.ACTIVE: {
        SubscriptionState.ACTIVE,
        SubscriptionState.PAUSED,
        SubscriptionState.DOWNGRADE_PENDING,
        SubscriptionState.CANCELLED,
        SubscriptionState.EXPIRED,
    },
    SubscriptionState.PAUSED: {
        SubscriptionState.ACTIVE,
        SubscriptionState.DOWNGRADE_PENDING,
        SubscriptionState.CANCELLED,
        SubscriptionState.EXPIRED,
    },
    SubscriptionState.DOWNGRADE_PENDING: {
        SubscriptionState.ACTIVE,
        SubscriptionState.PAUSED,
        SubscriptionState.CANCELLED,
        SubscriptionState.EXPIRED,
    },
    SubscriptionState.CANCELLED: {
        SubscriptionState.EXPIRED,
    },
    SubscriptionState.EXPIRED: set(),
}


class SubscriptionStateMachine:
    def __init__(self, initial_state: SubscriptionState = SubscriptionState.TRIAL) -> None:
        self._state = initial_state

    @property
    def state(self) -> SubscriptionState:
        return self._state

    def set_state(self, target: SubscriptionState) -> None:
        self._state = target

    def can_transition_to(self, target: SubscriptionState) -> bool:
        return target in _TRANSITIONS.get(self._state, set())

    def transition_to(self, target: SubscriptionState) -> None:
        if not self.can_transition_to(target):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target

    @staticmethod
    def get_valid_transitions(state: SubscriptionState) -> Set[SubscriptionState]:
        return _TRANSITIONS.get(state, set()).copy()
