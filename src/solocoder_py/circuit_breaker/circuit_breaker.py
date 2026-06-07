from __future__ import annotations

import threading
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Deque, Iterator, Optional

from ..ratelimiter.clock import Clock, SystemClock
from .models import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    StateChangeEvent,
    StateChangeReason,
    WindowStats,
)


@dataclass
class _CallRecord:
    timestamp: float
    duration: float
    success: bool
    slow: bool


class CircuitBreaker:
    def __init__(
        self,
        config: CircuitBreakerConfig,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config: CircuitBreakerConfig = config
        self._clock: Clock = clock or SystemClock()
        self._state: CircuitState = CircuitState.CLOSED
        self._state_change_time: float = self._clock.now()
        self._call_records: Deque[_CallRecord] = deque()
        self._half_open_probe_count: int = 0
        self._half_open_failure_observed: bool = False
        self._last_state_change_event: Optional[StateChangeEvent] = StateChangeEvent(
            previous_state=CircuitState.CLOSED,
            current_state=CircuitState.CLOSED,
            reason=StateChangeReason.INITIALIZED,
            timestamp=self._state_change_time,
        )
        self._lock: threading.RLock = threading.RLock()
        self._last_observed_time: float = self._clock.now()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_transition_open_to_half_open()
            return self._state

    @property
    def config(self) -> CircuitBreakerConfig:
        return self._config

    @property
    def last_state_change_event(self) -> Optional[StateChangeEvent]:
        return self._last_state_change_event

    def get_window_stats(self) -> WindowStats:
        with self._lock:
            current_time = self._clock.now()
            self._check_clock_backward(current_time)
            self._evict_expired(current_time)
            return self._compute_stats(current_time)

    def is_call_permitted(self) -> bool:
        with self._lock:
            self._maybe_transition_open_to_half_open()
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                return False
            if self._state == CircuitState.HALF_OPEN:
                return (
                    self._half_open_probe_count
                    < self._config.permitted_number_of_calls_in_half_open_state
                )
            return False

    @contextmanager
    def acquire(self) -> Iterator[None]:
        if not self.is_call_permitted():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is in {self._state.value} state"
            )
        start_time = self._clock.now()
        success = True
        try:
            yield
        except BaseException:
            success = False
            raise
        finally:
            end_time = self._clock.now()
            self._record_call(
                start_time=start_time,
                end_time=end_time,
                success=success,
            )

    def _record_call(
        self,
        start_time: float,
        end_time: float,
        success: bool,
    ) -> None:
        with self._lock:
            duration = end_time - start_time
            slow = duration >= self._config.slow_call_duration_threshold

            self._check_clock_backward(end_time)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_probe_count += 1
                if not success or slow:
                    self._half_open_failure_observed = True

                if self._half_open_failure_observed:
                    self._transition_to(
                        CircuitState.OPEN,
                        StateChangeReason.HALF_OPEN_FAILURE,
                    )
                elif (
                    self._half_open_probe_count
                    >= self._config.permitted_number_of_calls_in_half_open_state
                ):
                    self._transition_to(
                        CircuitState.CLOSED,
                        StateChangeReason.HALF_OPEN_SUCCESS,
                    )
                return

            if self._state == CircuitState.OPEN:
                return

            record = _CallRecord(
                timestamp=end_time,
                duration=duration,
                success=success,
                slow=slow,
            )
            self._call_records.append(record)
            self._evict_expired(end_time)

            if self._should_open(end_time):
                reason = self._get_open_reason(end_time)
                self._transition_to(CircuitState.OPEN, reason)

    def _should_open(self, current_time: float) -> bool:
        stats = self._compute_stats(current_time)
        if stats.total_count < self._config.minimum_number_of_calls:
            return False
        return (
            stats.failure_rate >= self._config.failure_rate_threshold
            or stats.slow_call_rate >= self._config.slow_call_rate_threshold
        )

    def _get_open_reason(self, current_time: float) -> StateChangeReason:
        stats = self._compute_stats(current_time)
        if stats.failure_rate >= self._config.failure_rate_threshold:
            return StateChangeReason.FAILURE_RATE_THRESHOLD_EXCEEDED
        if stats.slow_call_rate >= self._config.slow_call_rate_threshold:
            return StateChangeReason.SLOW_CALL_RATE_THRESHOLD_EXCEEDED
        return StateChangeReason.FAILURE_RATE_THRESHOLD_EXCEEDED

    def _maybe_transition_open_to_half_open(self) -> None:
        if (
            self._config.automatic_transition_from_open_to_half_open_enabled
            and self._state == CircuitState.OPEN
        ):
            current_time = self._clock.now()
            elapsed = current_time - self._state_change_time
            if elapsed >= self._config.wait_duration_in_open_state:
                self._transition_to(
                    CircuitState.HALF_OPEN,
                    StateChangeReason.COOLDOWN_COMPLETE,
                )

    def _transition_to(
        self,
        target_state: CircuitState,
        reason: StateChangeReason,
    ) -> None:
        previous_state = self._state
        self._state = target_state
        self._state_change_time = self._clock.now()

        if target_state == CircuitState.HALF_OPEN:
            self._half_open_probe_count = 0
            self._half_open_failure_observed = False

        if target_state == CircuitState.CLOSED:
            self._call_records.clear()

        current_time = self._clock.now()
        stats = None
        if self._call_records:
            stats = self._compute_stats(current_time)

        self._last_state_change_event = StateChangeEvent(
            previous_state=previous_state,
            current_state=target_state,
            reason=reason,
            timestamp=current_time,
            stats=stats,
        )

    def _evict_expired(self, current_time: float) -> None:
        cutoff = current_time - self._config.window_seconds
        while self._call_records and self._call_records[0].timestamp <= cutoff:
            self._call_records.popleft()

    def _check_clock_backward(self, current_time: float) -> None:
        if current_time < self._last_observed_time:
            self._call_records.clear()
        self._last_observed_time = current_time

    def _compute_stats(self, current_time: float) -> WindowStats:
        total = len(self._call_records)
        success_count = sum(1 for r in self._call_records if r.success)
        failure_count = total - success_count
        slow_count = sum(1 for r in self._call_records if r.slow)

        failure_rate = failure_count / total if total > 0 else 0.0
        slow_call_rate = slow_count / total if total > 0 else 0.0

        window_end = current_time
        window_start = window_end - self._config.window_seconds

        return WindowStats(
            total_count=total,
            success_count=success_count,
            failure_count=failure_count,
            slow_count=slow_count,
            failure_rate=failure_rate,
            slow_call_rate=slow_call_rate,
            window_start=window_start,
            window_end=window_end,
        )
