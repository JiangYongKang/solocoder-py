from __future__ import annotations

import random

import pytest

from solocoder_py.retry import (
    AttemptResult,
    ErrorCodePolicy,
    ExceptionTypePolicy,
    ManualClock,
    MaxAttemptsExceededError,
    NonRetryableError,
    RetryEngine,
    RetryStrategy,
)


class TransientError(Exception):
    pass


class FatalError(Exception):
    pass


class CodedError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class TestRetryEngineSuccess:
    def test_first_try_success_no_retries(self):
        clock = ManualClock()
        strategy = RetryStrategy(initial_delay=1.0, max_attempts=3)
        engine = RetryEngine(strategy=strategy, clock=clock)

        result = engine.execute(lambda: 42)
        assert result == 42
        assert engine.attempt_count == 1
        assert engine.attempts[0].result == AttemptResult.SUCCESS
        assert engine.attempts[0].error is None
        assert engine.attempts[0].next_scheduled_at is None
        assert clock.sleep_history == []

    def test_succeeds_after_two_failures(self):
        clock = ManualClock()
        strategy = RetryStrategy(
            initial_delay=1.0, backoff_multiplier=2.0, max_attempts=3
        )
        engine = RetryEngine(strategy=strategy, clock=clock)

        call_count = [0]

        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TransientError("temporary")
            return "success"

        result = engine.execute(flaky_func)
        assert result == "success"
        assert engine.attempt_count == 3

        attempts = engine.attempts
        assert attempts[0].result == AttemptResult.FAILURE
        assert isinstance(attempts[0].error, TransientError)
        assert attempts[0].next_scheduled_at is not None

        assert attempts[1].result == AttemptResult.FAILURE
        assert isinstance(attempts[1].error, TransientError)
        assert attempts[1].next_scheduled_at is not None

        assert attempts[2].result == AttemptResult.SUCCESS
        assert attempts[2].error is None
        assert attempts[2].next_scheduled_at is None

        assert clock.sleep_history == [1.0, 2.0]

    def test_passes_args_and_kwargs(self):
        engine = RetryEngine()

        def add(a, b, c=0):
            return a + b + c

        assert engine.execute(add, 1, 2, c=3) == 6


class TestRetryEngineMaxAttempts:
    def test_exceeds_max_attempts(self):
        clock = ManualClock()
        strategy = RetryStrategy(
            initial_delay=1.0, backoff_multiplier=2.0, max_attempts=3
        )
        engine = RetryEngine(strategy=strategy, clock=clock)

        call_count = [0]

        def always_fail():
            call_count[0] += 1
            raise TransientError("always fails")

        with pytest.raises(MaxAttemptsExceededError) as exc_info:
            engine.execute(always_fail)

        assert exc_info.value.attempts == 3
        assert call_count[0] == 3
        assert engine.attempt_count == 3
        assert all(a.result == AttemptResult.FAILURE for a in engine.attempts)
        assert engine.attempts[2].next_scheduled_at is None
        assert clock.sleep_history == [1.0, 2.0]

    def test_max_attempts_one_no_retries(self):
        clock = ManualClock()
        strategy = RetryStrategy(max_attempts=1)
        engine = RetryEngine(strategy=strategy, clock=clock)

        with pytest.raises(MaxAttemptsExceededError) as exc_info:
            engine.execute(lambda: (_ for _ in ()).throw(TransientError("fail")))

        assert exc_info.value.attempts == 1
        assert engine.attempt_count == 1
        assert clock.sleep_history == []


class TestRetryEngineNonRetryable:
    def test_non_retryable_exception_stops_immediately(self):
        clock = ManualClock()
        strategy = RetryStrategy(max_attempts=5)
        policy = ExceptionTypePolicy(non_retryable_exceptions=[FatalError])
        engine = RetryEngine(strategy=strategy, policy=policy, clock=clock)

        call_count = [0]

        def fatal_func():
            call_count[0] += 1
            raise FatalError("fatal")

        with pytest.raises(NonRetryableError) as exc_info:
            engine.execute(fatal_func)

        assert isinstance(exc_info.value.original_error, FatalError)
        assert call_count[0] == 1
        assert engine.attempt_count == 1
        assert engine.attempts[0].result == AttemptResult.NON_RETRYABLE_FAILURE
        assert engine.attempts[0].next_scheduled_at is None
        assert clock.sleep_history == []

    def test_error_code_policy_non_retryable(self):
        clock = ManualClock()
        policy = ErrorCodePolicy(non_retryable_codes=["BAD_REQUEST"])
        engine = RetryEngine(policy=policy, clock=clock)

        with pytest.raises(NonRetryableError):
            engine.execute(lambda: (_ for _ in ()).throw(CodedError("BAD_REQUEST")))

        assert engine.attempt_count == 1
        assert engine.attempts[0].result == AttemptResult.NON_RETRYABLE_FAILURE

    def test_mixed_transient_then_fatal(self):
        clock = ManualClock()
        strategy = RetryStrategy(
            initial_delay=1.0, backoff_multiplier=2.0, max_attempts=5
        )
        policy = ExceptionTypePolicy(non_retryable_exceptions=[FatalError])
        engine = RetryEngine(strategy=strategy, policy=policy, clock=clock)

        call_count = [0]

        def mixed_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TransientError("temporary")
            raise FatalError("now fatal")

        with pytest.raises(NonRetryableError):
            engine.execute(mixed_func)

        assert call_count[0] == 3
        assert engine.attempt_count == 3
        assert engine.attempts[0].result == AttemptResult.FAILURE
        assert engine.attempts[1].result == AttemptResult.FAILURE
        assert engine.attempts[2].result == AttemptResult.NON_RETRYABLE_FAILURE
        assert clock.sleep_history == [1.0, 2.0]


class TestRetryEngineTiming:
    def test_exponential_backoff_timing_without_jitter(self):
        clock = ManualClock()
        strategy = RetryStrategy(
            initial_delay=2.0, backoff_multiplier=3.0, max_delay=100.0, max_attempts=5
        )
        engine = RetryEngine(strategy=strategy, clock=clock)

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 5:
                raise TransientError("temp")
            return "ok"

        result = engine.execute(flaky)
        assert result == "ok"
        assert clock.sleep_history == [2.0, 6.0, 18.0, 54.0]

    def test_max_delay_capping_in_engine(self):
        clock = ManualClock()
        strategy = RetryStrategy(
            initial_delay=1.0, backoff_multiplier=2.0, max_delay=5.0, max_attempts=6
        )
        engine = RetryEngine(strategy=strategy, clock=clock)

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 6:
                raise TransientError("temp")
            return "ok"

        engine.execute(flaky)
        assert clock.sleep_history == [1.0, 2.0, 4.0, 5.0, 5.0]

    def test_jitter_deterministic_with_rng(self):
        clock = ManualClock()
        strategy = RetryStrategy(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            max_attempts=5,
            enable_jitter=True,
            jitter_ratio=0.3,
        )
        rng = random.Random(42)
        engine = RetryEngine(strategy=strategy, clock=clock, rng=rng)

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 5:
                raise TransientError("temp")
            return "ok"

        engine.execute(flaky)

        assert len(clock.sleep_history) == 4
        assert 0.7 <= clock.sleep_history[0] <= 1.3
        assert 1.4 <= clock.sleep_history[1] <= 2.6
        assert 2.8 <= clock.sleep_history[2] <= 5.2
        assert 5.6 <= clock.sleep_history[3] <= 10.4


class TestAttemptTracing:
    def test_full_trace_records_all_fields(self):
        clock = ManualClock(start_time=100.0)
        strategy = RetryStrategy(
            initial_delay=1.0, backoff_multiplier=2.0, max_attempts=3
        )
        engine = RetryEngine(strategy=strategy, clock=clock)

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TransientError(f"error-{call_count[0]}")
            return "done"

        engine.execute(flaky)
        attempts = engine.attempts

        assert len(attempts) == 3

        assert attempts[0].attempt_number == 1
        assert attempts[0].executed_at == 100.0
        assert attempts[0].result == AttemptResult.FAILURE
        assert isinstance(attempts[0].error, TransientError)
        assert attempts[0].next_scheduled_at == 101.0

        assert attempts[1].attempt_number == 2
        assert attempts[1].executed_at == 101.0
        assert attempts[1].result == AttemptResult.FAILURE
        assert isinstance(attempts[1].error, TransientError)
        assert attempts[1].next_scheduled_at == 103.0

        assert attempts[2].attempt_number == 3
        assert attempts[2].executed_at == 103.0
        assert attempts[2].result == AttemptResult.SUCCESS
        assert attempts[2].error is None
        assert attempts[2].next_scheduled_at is None

    def test_attempts_list_is_snapshot(self):
        engine = RetryEngine()
        engine.execute(lambda: 1)
        attempts1 = engine.attempts
        engine.execute(lambda: 2)
        attempts2 = engine.attempts
        assert len(attempts1) == 1
        assert len(attempts2) == 1


class TestEngineStateManagement:
    def test_reset_clears_attempts(self):
        engine = RetryEngine()
        engine.execute(lambda: 1)
        assert engine.attempt_count == 1
        engine.reset()
        assert engine.attempt_count == 0
        assert engine.attempts == []
        assert engine.last_attempt is None

    def test_execute_calls_reset_before_new_run(self):
        engine = RetryEngine()
        engine.execute(lambda: 1)
        assert engine.attempt_count == 1
        engine.execute(lambda: 2)
        assert engine.attempt_count == 1

    def test_last_attempt(self):
        engine = RetryEngine()
        assert engine.last_attempt is None
        engine.execute(lambda: 42)
        assert engine.last_attempt is not None
        assert engine.last_attempt.result == AttemptResult.SUCCESS

    def test_properties(self):
        clock = ManualClock()
        strategy = RetryStrategy(max_attempts=1)
        policy = ExceptionTypePolicy()
        engine = RetryEngine(strategy=strategy, policy=policy, clock=clock)
        assert engine.strategy is strategy
        assert engine.policy is policy
        assert engine.clock is clock
