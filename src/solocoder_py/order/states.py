from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class InvalidStateTransitionError(Exception):
    def __init__(self, current: "OrderState", target: "OrderState") -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


class OrderState(str, Enum):
    PENDING_PAYMENT = "待支付"
    PAID = "已支付"
    SHIPPED = "已发货"
    DELIVERED = "已签收"
    COMPLETED = "已完成"
    CANCELLED = "已取消"
    REFUNDING = "退款中"
    REFUNDED = "已退款"
    AFTER_SALE = "售后中"


_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
    OrderState.PENDING_PAYMENT: {
        OrderState.PAID,
        OrderState.CANCELLED,
    },
    OrderState.PAID: {
        OrderState.SHIPPED,
        OrderState.REFUNDING,
    },
    OrderState.SHIPPED: {
        OrderState.DELIVERED,
    },
    OrderState.DELIVERED: {
        OrderState.COMPLETED,
        OrderState.AFTER_SALE,
    },
    OrderState.COMPLETED: set(),
    OrderState.CANCELLED: set(),
    OrderState.REFUNDING: {
        OrderState.REFUNDED,
    },
    OrderState.REFUNDED: set(),
    OrderState.AFTER_SALE: {
        OrderState.REFUNDED,
        OrderState.COMPLETED,
    },
}


class OrderStateMachine:
    def __init__(self, initial_state: OrderState = OrderState.PENDING_PAYMENT) -> None:
        self._state = initial_state

    @property
    def state(self) -> OrderState:
        return self._state

    def can_transition_to(self, target: OrderState) -> bool:
        return target in _TRANSITIONS.get(self._state, set())

    def transition_to(self, target: OrderState) -> None:
        if not self.can_transition_to(target):
            raise InvalidStateTransitionError(self._state, target)
        self._state = target

    @staticmethod
    def get_valid_transitions(state: OrderState) -> Set[OrderState]:
        return _TRANSITIONS.get(state, set()).copy()
