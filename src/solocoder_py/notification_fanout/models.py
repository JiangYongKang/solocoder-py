from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .exceptions import InvalidChannelConfigError


class BackoffType(str, Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class ChannelDeliveryStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Notification:
    notification_id: str
    title: str
    content: str
    recipient: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelConfig:
    channel_name: str
    timeout: float = 5.0
    max_attempts: int = 3
    backoff_type: BackoffType = BackoffType.EXPONENTIAL
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    fixed_interval: float = 1.0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.channel_name or not self.channel_name.strip():
            raise InvalidChannelConfigError("channel_name cannot be empty")
        if self.timeout <= 0:
            raise InvalidChannelConfigError("timeout must be positive")
        if self.max_attempts < 1:
            raise InvalidChannelConfigError("max_attempts must be at least 1")
        if self.backoff_type not in (BackoffType.FIXED, BackoffType.EXPONENTIAL):
            raise InvalidChannelConfigError(
                f"Invalid backoff_type: {self.backoff_type}"
            )
        if self.initial_delay <= 0:
            raise InvalidChannelConfigError("initial_delay must be positive")
        if self.backoff_multiplier < 1.0:
            raise InvalidChannelConfigError(
                "backoff_multiplier must be >= 1.0"
            )
        if self.max_delay <= 0:
            raise InvalidChannelConfigError("max_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise InvalidChannelConfigError(
                "max_delay must be >= initial_delay"
            )
        if self.fixed_interval <= 0:
            raise InvalidChannelConfigError("fixed_interval must be positive")

    def calculate_delay(self, attempt_number: int) -> float:
        if attempt_number < 1:
            raise ValueError("attempt_number must be >= 1")
        if attempt_number == 1:
            return 0.0

        if self.backoff_type == BackoffType.FIXED:
            return self.fixed_interval

        exponent = attempt_number - 2
        raw_delay = self.initial_delay * (self.backoff_multiplier ** exponent)
        return min(raw_delay, self.max_delay)


@dataclass
class ChannelAttempt:
    attempt_number: int
    executed_at: float
    success: bool
    error: Optional[Exception] = None
    duration: float = 0.0


@dataclass
class ChannelResult:
    channel_name: str
    status: ChannelDeliveryStatus
    attempts: int
    attempts_detail: list[ChannelAttempt] = field(default_factory=list)
    final_error: Optional[Exception] = None
    total_duration: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.status == ChannelDeliveryStatus.SUCCESS

    @property
    def failed(self) -> bool:
        return self.status in (
            ChannelDeliveryStatus.FAILED,
            ChannelDeliveryStatus.TIMEOUT,
        )


@dataclass
class FanoutResult:
    notification_id: str
    channel_results: dict[str, ChannelResult] = field(default_factory=dict)
    total_duration: float = 0.0

    @property
    def succeeded_channels(self) -> list[ChannelResult]:
        return [r for r in self.channel_results.values() if r.succeeded]

    @property
    def failed_channels(self) -> list[ChannelResult]:
        return [r for r in self.channel_results.values() if r.failed]

    @property
    def all_succeeded(self) -> bool:
        return all(r.succeeded for r in self.channel_results.values())

    @property
    def any_failed(self) -> bool:
        return any(r.failed for r in self.channel_results.values())

    @property
    def channel_count(self) -> int:
        return len(self.channel_results)

    @property
    def succeeded_count(self) -> int:
        return len(self.succeeded_channels)

    @property
    def failed_count(self) -> int:
        return len(self.failed_channels)

    def summary(self) -> dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "channel_count": self.channel_count,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "all_succeeded": self.all_succeeded,
            "total_duration": self.total_duration,
            "channels": {
                name: {
                    "status": result.status.value,
                    "attempts": result.attempts,
                    "total_duration": result.total_duration,
                    "error": str(result.final_error) if result.final_error else None,
                }
                for name, result in self.channel_results.items()
            },
        }
