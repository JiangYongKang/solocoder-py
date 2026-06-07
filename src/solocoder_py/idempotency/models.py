from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .clock import Clock, SystemClock


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
    created_at: float = field(default_factory=lambda: SystemClock().now())
    expires_at: float = field(
        default_factory=lambda: SystemClock().now() + 86400.0
    )

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key cannot be empty")
        if not self.request_fingerprint:
            raise ValueError("request_fingerprint cannot be empty")
        if self.expires_at <= self.created_at and self.state != IdempotencyState.EXPIRED:
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

    def is_expired(self, clock: Optional[Clock] = None) -> bool:
        if self.state == IdempotencyState.EXPIRED:
            return True
        effective_clock = clock if clock is not None else SystemClock()
        return effective_clock.now() >= self.expires_at

    def remaining_ttl(self, clock: Optional[Clock] = None) -> float:
        effective_clock = clock if clock is not None else SystemClock()
        remaining = self.expires_at - effective_clock.now()
        if remaining < 0:
            return 0.0
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

    def refresh_ttl(self, ttl_seconds: float, clock: Optional[Clock] = None) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl must be positive")
        effective_clock = clock if clock is not None else SystemClock()
        self.expires_at = effective_clock.now() + ttl_seconds

    def snapshot(self) -> "IdempotencyRecord":
        return IdempotencyRecord(
            key=self.key,
            request_fingerprint=self.request_fingerprint,
            state=self.state,
            response_data=self.response_data,
            error_message=self.error_message,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )
