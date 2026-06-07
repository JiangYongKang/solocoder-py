from __future__ import annotations

from dataclasses import dataclass


_TOKEN_SCALE = 1_000_000


def tokens_to_scaled(tokens: float) -> int:
    return int(round(tokens * _TOKEN_SCALE))


def scaled_to_tokens(scaled: int) -> float:
    return scaled / _TOKEN_SCALE


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

    @property
    def capacity_scaled(self) -> int:
        return self.capacity * _TOKEN_SCALE

    @property
    def refill_rate_scaled_per_second(self) -> float:
        return self.refill_rate_per_second * _TOKEN_SCALE


@dataclass
class TokenBucketState:
    current_tokens_scaled: int
    last_refill_time: float
