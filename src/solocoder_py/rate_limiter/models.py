from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RateLimiterError(Exception):
    pass


class InvalidConfigError(RateLimiterError):
    pass


class TokenExhaustedError(RateLimiterError):
    def __init__(self, retry_after: Optional[float] = None) -> None:
        self.retry_after = retry_after
        if retry_after is not None:
            super().__init__(f"Tokens exhausted, retry after {retry_after:.2f}s")
        else:
            super().__init__("Tokens exhausted")


class WaitTimeoutError(RateLimiterError):
    def __init__(self, waited: float, timeout: float) -> None:
        self.waited = waited
        self.timeout = timeout
        super().__init__(f"Wait timed out after {waited:.2f}s (timeout={timeout:.2f}s)")


class InvalidResponseHeaderError(RateLimiterError):
    def __init__(self, header_name: str, value: Any) -> None:
        self.header_name = header_name
        self.value = value
        super().__init__(f"Invalid response header '{header_name}': {value}")


class SyncStrategy(str, Enum):
    MIN = "min"
    SERVER = "server"
    LOCAL = "local"


@dataclass
class TokenBucketConfig:
    refill_rate: float
    capacity: int
    initial_tokens: Optional[int] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.refill_rate <= 0:
            raise InvalidConfigError("refill_rate must be positive")
        if self.capacity <= 0:
            raise InvalidConfigError("capacity must be positive")
        if self.initial_tokens is not None:
            if self.initial_tokens < 0:
                raise InvalidConfigError("initial_tokens must be non-negative")
            if self.initial_tokens > self.capacity:
                raise InvalidConfigError("initial_tokens cannot exceed capacity")


@dataclass
class RateLimitHeaders:
    remaining: Optional[int] = None
    limit: Optional[int] = None
    reset: Optional[float] = None
    retry_after: Optional[float] = None
    raw_headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_headers(cls, headers: Dict[str, Any]) -> "RateLimitHeaders":
        result = cls(raw_headers={})
        lowered = {k.lower(): v for k, v in headers.items()}
        result.raw_headers = {k: str(v) for k, v in headers.items()}

        if "x-ratelimit-remaining" in lowered:
            try:
                result.remaining = int(lowered["x-ratelimit-remaining"])
            except (ValueError, TypeError):
                raise InvalidResponseHeaderError(
                    "X-RateLimit-Remaining", lowered["x-ratelimit-remaining"]
                )

        if "x-ratelimit-limit" in lowered:
            try:
                result.limit = int(lowered["x-ratelimit-limit"])
            except (ValueError, TypeError):
                raise InvalidResponseHeaderError(
                    "X-RateLimit-Limit", lowered["x-ratelimit-limit"]
                )

        if "x-ratelimit-reset" in lowered:
            val = lowered["x-ratelimit-reset"]
            try:
                result.reset = float(val)
            except (ValueError, TypeError):
                raise InvalidResponseHeaderError(
                    "X-RateLimit-Reset", lowered["x-ratelimit-reset"]
                )

        if "retry-after" in lowered:
            val = lowered["retry-after"]
            try:
                result.retry_after = float(val)
            except (ValueError, TypeError):
                raise InvalidResponseHeaderError(
                    "Retry-After", lowered["retry-after"]
                )

        return result


@dataclass
class AcquireResult:
    acquired: bool
    tokens_consumed: int
    tokens_remaining: int
    wait_time: float = 0.0
    retry_after: Optional[float] = None


@dataclass
class TokenBucketState:
    capacity: int
    refill_rate: float
    tokens: float
    last_refill_time: float
