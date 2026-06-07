from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class StateChangeReason(str, Enum):
    INITIALIZED = "INITIALIZED"
    FAILURE_RATE_THRESHOLD_EXCEEDED = "FAILURE_RATE_THRESHOLD_EXCEEDED"
    SLOW_CALL_RATE_THRESHOLD_EXCEEDED = "SLOW_CALL_RATE_THRESHOLD_EXCEEDED"
    COOLDOWN_COMPLETE = "COOLDOWN_COMPLETE"
    HALF_OPEN_SUCCESS = "HALF_OPEN_SUCCESS"
    HALF_OPEN_FAILURE = "HALF_OPEN_FAILURE"


class CircuitBreakerError(Exception):
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    pass


class InvalidConfigError(CircuitBreakerError):
    pass


@dataclass(frozen=True)
class WindowStats:
    total_count: int
    success_count: int
    failure_count: int
    slow_count: int
    failure_rate: float
    slow_call_rate: float
    window_start: float
    window_end: float


@dataclass
class CircuitBreakerConfig:
    window_seconds: float
    minimum_number_of_calls: int
    failure_rate_threshold: float
    slow_call_duration_threshold: float
    slow_call_rate_threshold: float
    permitted_number_of_calls_in_half_open_state: int
    wait_duration_in_open_state: float
    automatic_transition_from_open_to_half_open_enabled: bool = True

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.window_seconds <= 0:
            raise InvalidConfigError("window_seconds must be positive")
        if self.minimum_number_of_calls <= 0:
            raise InvalidConfigError("minimum_number_of_calls must be positive")
        if self.failure_rate_threshold <= 0 or self.failure_rate_threshold > 1:
            raise InvalidConfigError(
                "failure_rate_threshold must be in (0, 1]"
            )
        if self.slow_call_duration_threshold <= 0:
            raise InvalidConfigError(
                "slow_call_duration_threshold must be positive"
            )
        if self.slow_call_rate_threshold <= 0 or self.slow_call_rate_threshold > 1:
            raise InvalidConfigError(
                "slow_call_rate_threshold must be in (0, 1]"
            )
        if self.permitted_number_of_calls_in_half_open_state <= 0:
            raise InvalidConfigError(
                "permitted_number_of_calls_in_half_open_state must be positive"
            )
        if self.wait_duration_in_open_state <= 0:
            raise InvalidConfigError(
                "wait_duration_in_open_state must be positive"
            )


@dataclass
class StateChangeEvent:
    previous_state: CircuitState
    current_state: CircuitState
    reason: StateChangeReason
    timestamp: float
    stats: Optional[WindowStats] = None
