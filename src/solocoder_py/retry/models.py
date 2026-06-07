from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .exceptions import InvalidRetryStrategyError


class AttemptResult:
    SUCCESS = "success"
    FAILURE = "failure"
    NON_RETRYABLE_FAILURE = "non_retryable_failure"


@dataclass
class AttemptRecord:
    attempt_number: int
    executed_at: float
    result: str
    error: Optional[Exception] = None
    next_scheduled_at: Optional[float] = None


@dataclass
class RetryStrategy:
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    max_attempts: int = 3
    enable_jitter: bool = False
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.initial_delay <= 0:
            raise InvalidRetryStrategyError("initial_delay must be positive")
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
        if self.max_attempts < 1:
            raise InvalidRetryStrategyError("max_attempts must be at least 1")
        if self.jitter_ratio < 0 or self.jitter_ratio > 1.0:
            raise InvalidRetryStrategyError(
                "jitter_ratio must be between 0 and 1 (inclusive)"
            )

    def calculate_delay(self, attempt_number: int, rng: Optional[random.Random] = None) -> float:
        if attempt_number <= 1:
            return 0.0

        exponent = attempt_number - 2
        raw_delay = self.initial_delay * (self.backoff_multiplier ** exponent)
        delay = min(raw_delay, self.max_delay)

        if self.enable_jitter and self.jitter_ratio > 0:
            rand_source = rng if rng is not None else random
            jitter_range = delay * self.jitter_ratio
            base = delay - jitter_range
            jitter_amount = rand_source.uniform(0, jitter_range * 2)
            delay = base + jitter_amount

        return max(0.0, delay)

    def should_attempt(self, attempt_number: int) -> bool:
        return attempt_number <= self.max_attempts

    def __repr__(self) -> str:
        return (
            f"RetryStrategy(initial_delay={self.initial_delay}, "
            f"backoff_multiplier={self.backoff_multiplier}, "
            f"max_delay={self.max_delay}, "
            f"max_attempts={self.max_attempts}, "
            f"enable_jitter={self.enable_jitter}, "
            f"jitter_ratio={self.jitter_ratio})"
        )
