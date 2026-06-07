from __future__ import annotations

from dataclasses import dataclass


class TokenBucketError(Exception):
    pass


class InvalidBucketConfigError(TokenBucketError):
    pass


class NotEnoughTokensError(TokenBucketError):
    def __init__(self, requested: int, available: float) -> None:
        self.requested = requested
        self.available = available
        super().__init__(
            f"Not enough tokens: requested {requested}, available {available}"
        )


@dataclass(frozen=True)
class TokenBucketConfig:
    capacity: int
    refill_rate_per_second: float

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise InvalidBucketConfigError("capacity must be positive")
        if self.refill_rate_per_second < 0:
            raise InvalidBucketConfigError("refill_rate_per_second must be non-negative")


@dataclass
class TokenBucketState:
    current_tokens: float
    last_refill_time: float
