from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

from .exceptions import (
    InvalidRetryStrategyError,
    InvalidSigningSecretError,
    InvalidUrlError,
)


class DeliveryStatus:
    PENDING = "pending"
    DELIVERING = "delivering"
    SUCCESS = "success"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class RetryStrategy:
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.initial_delay < 0:
            raise InvalidRetryStrategyError("initial_delay must be non-negative")
        if self.backoff_multiplier < 1.0:
            raise InvalidRetryStrategyError(
                "backoff_multiplier must be greater than or equal to 1.0"
            )
        if self.max_delay <= 0:
            raise InvalidRetryStrategyError("max_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise InvalidRetryStrategyError(
                "max_delay must be greater than or equal to initial_delay"
            )
        if self.max_retries < 0:
            raise InvalidRetryStrategyError("max_retries must be non-negative")

    def calculate_delay(self, attempt_number: int) -> float:
        if attempt_number <= 0:
            raise ValueError("attempt_number must be >= 1")

        if attempt_number == 1:
            return 0.0

        exponent = attempt_number - 2
        raw_delay = self.initial_delay * (self.backoff_multiplier ** exponent)
        return min(raw_delay, self.max_delay)

    def should_retry(self, failure_count: int) -> bool:
        return failure_count <= self.max_retries


def _is_valid_url(url: str) -> bool:
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


@dataclass
class WebhookTarget:
    id: str
    url: str
    signing_secret: str
    retry_strategy: RetryStrategy = field(default_factory=RetryStrategy)
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id cannot be empty")
        if not _is_valid_url(self.url):
            raise InvalidUrlError(f"Invalid webhook URL: {self.url}")
        if not isinstance(self.signing_secret, str) or not self.signing_secret:
            raise InvalidSigningSecretError("signing_secret must be a non-empty string")


@dataclass
class WebhookMessage:
    id: str
    target_id: str
    event_type: str
    payload: Mapping[str, Any]
    created_at: float
    delivery_attempts: int = 0
    last_error: Optional[str] = None
    next_delivery_at: Optional[float] = None
    status: str = DeliveryStatus.PENDING

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.target_id:
            raise ValueError("target_id cannot be empty")
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if self.delivery_attempts < 0:
            raise ValueError("delivery_attempts cannot be negative")

    @property
    def is_pending(self) -> bool:
        return self.status == DeliveryStatus.PENDING

    @property
    def is_delivering(self) -> bool:
        return self.status == DeliveryStatus.DELIVERING

    @property
    def is_success(self) -> bool:
        return self.status == DeliveryStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status == DeliveryStatus.FAILED

    @property
    def is_dead_letter(self) -> bool:
        return self.status == DeliveryStatus.DEAD_LETTER


@dataclass
class DeliveryAttempt:
    id: str
    message_id: str
    target_id: str
    attempted_at: float
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    response_body: Optional[str] = None


@dataclass
class DeadLetterMessage:
    message_id: str
    target_id: str
    event_type: str
    payload: Mapping[str, Any]
    failure_count: int
    last_error: str
    moved_to_dead_letter_at: float
    delivery_history: list[DeliveryAttempt] = field(default_factory=list)


@dataclass
class SignedRequest:
    target_id: str
    url: str
    payload: Mapping[str, Any]
    signature: str
    timestamp: float
    event_type: str
    message_id: str

    @property
    def headers(self) -> dict[str, str]:
        return {
            "X-Webhook-Signature": self.signature,
            "X-Webhook-Timestamp": str(self.timestamp),
            "X-Webhook-Event-Type": self.event_type,
            "X-Webhook-Message-Id": self.message_id,
            "Content-Type": "application/json",
        }


def generate_message_id() -> str:
    return f"msg_{uuid.uuid4().hex}"


def generate_target_id() -> str:
    return f"tgt_{uuid.uuid4().hex}"


def generate_delivery_attempt_id() -> str:
    return f"att_{uuid.uuid4().hex}"
