from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class MessageStatus(str, Enum):
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    DEAD_LETTER = "dead_letter"


class QueueError(Exception):
    pass


class MessageNotFoundError(QueueError):
    pass


class DuplicateMessageError(QueueError):
    pass


@dataclass
class Message:
    id: str
    body: Any
    queue_name: str
    priority: int = 0
    deliver_at: Optional[datetime] = None
    visibility_timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    max_retry_count: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    status: MessageStatus = MessageStatus.PENDING
    receive_count: int = 0
    invisible_until: Optional[datetime] = None
    first_received_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Message id cannot be empty")
        if not self.queue_name:
            raise ValueError("queue_name cannot be empty")
        if self.max_retry_count < 0:
            raise ValueError("max_retry_count cannot be negative")
        if self.receive_count < 0:
            raise ValueError("receive_count cannot be negative")

    @property
    def is_delayed(self) -> bool:
        if self.deliver_at is None:
            return False
        return datetime.now() < self.deliver_at

    @property
    def is_visible(self) -> bool:
        if self.invisible_until is None:
            return True
        return datetime.now() >= self.invisible_until

    @property
    def is_dead(self) -> bool:
        return self.receive_count > self.max_retry_count

    def mark_received(self, visibility_timeout: Optional[timedelta] = None) -> None:
        self.receive_count += 1
        timeout = visibility_timeout or self.visibility_timeout
        self.invisible_until = datetime.now() + timeout
        self.status = MessageStatus.IN_FLIGHT
        if self.first_received_at is None:
            self.first_received_at = datetime.now()

    def make_visible(self) -> None:
        self.invisible_until = None
        self.status = MessageStatus.PENDING

    def mark_dead_letter(self) -> None:
        self.status = MessageStatus.DEAD_LETTER
        self.invisible_until = None
