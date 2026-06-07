from __future__ import annotations

import random
from typing import Any, Callable, Optional

from .clock import Clock, SystemClock
from .exceptions import (
    MaxAttemptsExceededError,
    NonRetryableError,
)
from .models import AttemptRecord, AttemptResult, RetryStrategy
from .policy import RetryAllPolicy, RetryPolicy


class RetryEngine:
    def __init__(
        self,
        strategy: Optional[RetryStrategy] = None,
        policy: Optional[RetryPolicy] = None,
        clock: Optional[Clock] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._strategy = strategy or RetryStrategy()
        self._policy = policy or RetryAllPolicy()
        self._clock = clock or SystemClock()
        self._rng = rng

        self._attempts: list[AttemptRecord] = []

    @property
    def strategy(self) -> RetryStrategy:
        return self._strategy

    @property
    def policy(self) -> RetryPolicy:
        return self._policy

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def attempts(self) -> list[AttemptRecord]:
        return list(self._attempts)

    @property
    def attempt_count(self) -> int:
        return len(self._attempts)

    @property
    def last_attempt(self) -> Optional[AttemptRecord]:
        if self._attempts:
            return self._attempts[-1]
        return None

    def reset(self) -> None:
        self._attempts.clear()

    def _current_run_attempt_count(self) -> int:
        count = 0
        for record in reversed(self._attempts):
            if record.result in (
                AttemptResult.SUCCESS,
                AttemptResult.NON_RETRYABLE_FAILURE,
            ):
                break
            count += 1
        return count

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        attempt_number = self._current_run_attempt_count() + 1

        while True:
            if not self._strategy.should_attempt(attempt_number):
                raise MaxAttemptsExceededError(attempts=attempt_number - 1)

            executed_at = self._clock.now()

            try:
                result = func(*args, **kwargs)
                record = AttemptRecord(
                    attempt_number=attempt_number,
                    executed_at=executed_at,
                    result=AttemptResult.SUCCESS,
                    error=None,
                    next_scheduled_at=None,
                )
                self._attempts.append(record)
                return result
            except Exception as exc:
                if not self._policy.is_retryable(exc):
                    record = AttemptRecord(
                        attempt_number=attempt_number,
                        executed_at=executed_at,
                        result=AttemptResult.NON_RETRYABLE_FAILURE,
                        error=exc,
                        next_scheduled_at=None,
                    )
                    self._attempts.append(record)
                    raise NonRetryableError(original_error=exc) from exc

                next_attempt = attempt_number + 1
                if not self._strategy.should_attempt(next_attempt):
                    record = AttemptRecord(
                        attempt_number=attempt_number,
                        executed_at=executed_at,
                        result=AttemptResult.FAILURE,
                        error=exc,
                        next_scheduled_at=None,
                    )
                    self._attempts.append(record)
                    raise MaxAttemptsExceededError(attempts=attempt_number) from exc

                delay = self._strategy.calculate_delay(next_attempt, rng=self._rng)
                next_scheduled_at = self._clock.now() + delay

                record = AttemptRecord(
                    attempt_number=attempt_number,
                    executed_at=executed_at,
                    result=AttemptResult.FAILURE,
                    error=exc,
                    next_scheduled_at=next_scheduled_at,
                )
                self._attempts.append(record)

                if delay > 0:
                    self._clock.sleep(delay)

                attempt_number = next_attempt
