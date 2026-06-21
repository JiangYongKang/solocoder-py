from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class CommandStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    TIMEOUT = "timeout"


class CmdQueueError(Exception):
    pass


class CommandNotFoundError(CmdQueueError):
    pass


class DuplicateCommandError(CmdQueueError):
    pass


class InvalidTtlError(CmdQueueError):
    pass


@dataclass
class Command:
    id: str
    payload: Any
    ttl: Optional[float] = None
    status: CommandStatus = CommandStatus.PENDING
    enqueued_at: float = field(default_factory=time.time)
    sent_at: Optional[float] = None
    delivered_at: Optional[float] = None
    timed_out_at: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Command id cannot be empty")
        if self.ttl is not None and self.ttl < 0:
            raise InvalidTtlError("TTL cannot be negative")

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() - self.enqueued_at >= self.ttl

    def mark_sent(self) -> None:
        if self.status in (CommandStatus.DELIVERED, CommandStatus.TIMEOUT):
            return
        self.status = CommandStatus.SENT
        self.sent_at = time.time()

    def mark_delivered(self) -> bool:
        if self.status == CommandStatus.DELIVERED:
            return False
        if self.status == CommandStatus.TIMEOUT:
            return False
        if self.status != CommandStatus.SENT:
            raise CmdQueueError(
                f"Cannot mark command as DELIVERED from status {self.status}. "
                f"Only SENT commands can be marked as DELIVERED."
            )
        self.status = CommandStatus.DELIVERED
        self.delivered_at = time.time()
        return True

    def mark_timeout(self) -> bool:
        if self.status == CommandStatus.DELIVERED:
            return False
        if self.status == CommandStatus.TIMEOUT:
            return False
        if self.status != CommandStatus.SENT:
            raise CmdQueueError(
                f"Cannot mark command as TIMEOUT from status {self.status}. "
                f"Only SENT commands can be marked as TIMEOUT."
            )
        self.status = CommandStatus.TIMEOUT
        self.timed_out_at = time.time()
        return True

    def _mark_ttl_expired(self) -> bool:
        if self.status == CommandStatus.DELIVERED:
            return False
        if self.status == CommandStatus.TIMEOUT:
            return False
        if self.status != CommandStatus.PENDING:
            return False
        self.status = CommandStatus.TIMEOUT
        self.timed_out_at = time.time()
        return True
