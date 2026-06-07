from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class IdempotencyState(str, Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"


class FailureReplayPolicy(str, Enum):
    REPLAY = "replay"
    REJECT = "reject"
    RETRY = "retry"


@dataclass
class IdempotencyRecord:
    key: str
    request_fingerprint: str
    state: IdempotencyState = IdempotencyState.PROCESSING
    response_data: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key cannot be empty")
        if not self.request_fingerprint:
            raise ValueError("request_fingerprint cannot be empty")
        if self.state != IdempotencyState.EXPIRED and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")

    @property
    def is_processing(self) -> bool:
        return self.state == IdempotencyState.PROCESSING

    @property
    def is_success(self) -> bool:
        return self.state == IdempotencyState.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.state == IdempotencyState.FAILED

    @property
    def is_expired(self) -> bool:
        if self.state == IdempotencyState.EXPIRED:
            return True
        return datetime.now() >= self.expires_at

    @property
    def remaining_ttl(self) -> Optional[timedelta]:
        remaining = self.expires_at - datetime.now()
        if remaining.total_seconds() < 0:
            return timedelta(seconds=0)
        return remaining

    def fingerprint_matches(self, fingerprint: str) -> bool:
        return self.request_fingerprint == fingerprint

    def mark_success(self, response_data: Any) -> None:
        if self.state != IdempotencyState.PROCESSING:
            raise ValueError(f"Cannot mark success from state {self.state}")
        self.state = IdempotencyState.SUCCESS
        self.response_data = response_data
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        if self.state != IdempotencyState.PROCESSING:
            raise ValueError(f"Cannot mark failed from state {self.state}")
        self.state = IdempotencyState.FAILED
        self.error_message = error_message
        self.response_data = None

    def mark_expired(self) -> None:
        self.state = IdempotencyState.EXPIRED

    def refresh_ttl(self, ttl: timedelta) -> None:
        if ttl.total_seconds() <= 0:
            raise ValueError("ttl must be positive")
        self.expires_at = datetime.now() + ttl
