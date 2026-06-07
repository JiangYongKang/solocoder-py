from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .states import OutboxMessageState, OutboxStateMachine


@dataclass
class BusinessRecord:
    id: str
    business_type: str
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.business_type:
            raise ValueError("business_type cannot be empty")


@dataclass
class OutboxMessage:
    id: str
    business_record_id: str
    message_type: str
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    _state_machine: OutboxStateMachine = field(
        default_factory=lambda: OutboxStateMachine(OutboxMessageState.PENDING)
    )

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.business_record_id:
            raise ValueError("business_record_id cannot be empty")
        if not self.message_type:
            raise ValueError("message_type cannot be empty")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")

    @property
    def state(self) -> OutboxMessageState:
        return self._state_machine.state

    @property
    def is_pending(self) -> bool:
        return self.state == OutboxMessageState.PENDING

    @property
    def is_delivering(self) -> bool:
        return self.state == OutboxMessageState.DELIVERING

    @property
    def is_confirmed(self) -> bool:
        return self.state == OutboxMessageState.CONFIRMED

    @property
    def is_failed(self) -> bool:
        return self.state == OutboxMessageState.FAILED

    @property
    def is_dead_letter(self) -> bool:
        return self.state == OutboxMessageState.DEAD_LETTER

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def can_transition_to(self, target: OutboxMessageState) -> bool:
        return self._state_machine.can_transition_to(target)

    def transition_to(self, target: OutboxMessageState) -> None:
        self._state_machine.transition_to(target)

    def mark_delivering(self, worker_id: str) -> None:
        self.transition_to(OutboxMessageState.DELIVERING)
        self.claimed_by = worker_id
        self.claimed_at = datetime.now()

    def mark_confirmed(self) -> None:
        self.transition_to(OutboxMessageState.CONFIRMED)
        self.claimed_by = None
        self.claimed_at = None

    def mark_failed(self, error: str, retry_delay_seconds: int = 5) -> None:
        self.transition_to(OutboxMessageState.FAILED)
        self.retry_count += 1
        self.last_error = error
        self.claimed_by = None
        self.claimed_at = None
        if self.can_retry:
            self.next_retry_at = datetime.now() + _seconds_to_timedelta(retry_delay_seconds)
        else:
            self.next_retry_at = None

    def mark_dead_letter(self) -> None:
        self.transition_to(OutboxMessageState.DEAD_LETTER)
        self.next_retry_at = None

    def release_claim(self) -> None:
        self.claimed_by = None
        self.claimed_at = None


def _seconds_to_timedelta(seconds: int):
    from datetime import timedelta
    return timedelta(seconds=seconds)
