from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class InvalidStateTransitionError(Exception):
    def __init__(self, current: "RefundState", target: "RefundState") -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


class RefundState(str, Enum):
    REFUND_REQUESTED = "退款申请"
    UNDER_REVIEW = "审核中"
    REFUNDED = "已退款"
    REJECTED = "已拒绝"
    CHARGED_BACK = "已拒付"
    CANCELLED = "已取消"


_TRANSITIONS: Dict[RefundState, Set[RefundState]] = {
    RefundState.REFUND_REQUESTED: {
        RefundState.UNDER_REVIEW,
        RefundState.CANCELLED,
    },
    RefundState.UNDER_REVIEW: {
        RefundState.REFUNDED,
        RefundState.REJECTED,
        RefundState.CHARGED_BACK,
    },
    RefundState.REFUNDED: {
        RefundState.CHARGED_BACK,
    },
    RefundState.REJECTED: set(),
    RefundState.CHARGED_BACK: set(),
    RefundState.CANCELLED: set(),
}


class RefundStateMachine:
    def __init__(
        self, initial_state: RefundState = RefundState.REFUND_REQUESTED
    ) -> None:
        self._state = initial_state

    @property
    def state(self) -> RefundState:
        return self._state

    def can_transition_to(self, target: RefundState) -> bool:
        return target in _TRANSITIONS.get(self._state, set())

    def transition_to(self, target: RefundState) -> None:
        if not self.can_transition_to(target):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target

    @staticmethod
    def get_valid_transitions(state: RefundState) -> Set[RefundState]:
        return _TRANSITIONS.get(state, set()).copy()
