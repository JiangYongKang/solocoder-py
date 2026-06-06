from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class LockState(str, Enum):
    FREE = "free"
    HELD = "held"
    EXPIRED = "expired"


@dataclass
class LockEntry:
    lock_name: str
    state: LockState = LockState.FREE
    client_id: Optional[str] = None
    fence_token: int = 0
    reentrant_count: int = 0
    lease_expires_at: Optional[datetime] = None
    acquired_at: Optional[datetime] = None
    lease_duration: timedelta = field(default_factory=lambda: timedelta(seconds=30))

    def __post_init__(self) -> None:
        if not self.lock_name:
            raise ValueError("lock_name cannot be empty")
        if self.reentrant_count < 0:
            raise ValueError("reentrant_count cannot be negative")
        if self.fence_token < 0:
            raise ValueError("fence_token cannot be negative")

    @property
    def is_held(self) -> bool:
        if self.state != LockState.HELD:
            return False
        if self.lease_expires_at is None:
            return False
        return datetime.now() < self.lease_expires_at

    @property
    def is_expired(self) -> bool:
        if self.state == LockState.FREE:
            return False
        if self.lease_expires_at is None:
            return False
        return datetime.now() >= self.lease_expires_at

    @property
    def remaining_lease(self) -> Optional[timedelta]:
        if self.lease_expires_at is None:
            return None
        remaining = self.lease_expires_at - datetime.now()
        if remaining.total_seconds() < 0:
            return timedelta(seconds=0)
        return remaining

    def is_held_by(self, client_id: str) -> bool:
        if not self.is_held:
            return False
        return self.client_id == client_id

    def acquire(
        self,
        client_id: str,
        fence_token: int,
        lease_duration: timedelta,
    ) -> None:
        self.client_id = client_id
        self.fence_token = fence_token
        self.reentrant_count = 1
        self.state = LockState.HELD
        self.lease_duration = lease_duration
        self.lease_expires_at = datetime.now() + lease_duration
        self.acquired_at = datetime.now()

    def reenter(self, lease_duration: Optional[timedelta] = None) -> None:
        self.reentrant_count += 1
        duration = lease_duration if lease_duration is not None else self.lease_duration
        self.lease_duration = duration
        self.lease_expires_at = datetime.now() + duration

    def release_one(self) -> bool:
        if self.reentrant_count <= 1:
            self._reset()
            return True
        self.reentrant_count -= 1
        return False

    def force_release(self) -> None:
        self._reset()

    def renew(self, lease_duration: Optional[timedelta] = None) -> None:
        duration = lease_duration if lease_duration is not None else self.lease_duration
        self.lease_duration = duration
        self.lease_expires_at = datetime.now() + duration

    def mark_expired(self) -> None:
        self.state = LockState.EXPIRED

    def _reset(self) -> None:
        self.client_id = None
        self.reentrant_count = 0
        self.state = LockState.FREE
        self.lease_expires_at = None
        self.acquired_at = None
