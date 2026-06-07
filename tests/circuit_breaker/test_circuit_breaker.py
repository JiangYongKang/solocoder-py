from __future__ import annotations

import pytest

from solocoder_py.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    InvalidConfigError,
    ManualClock,
    StateChangeReason,
)


def _make_config(
    *,
    window_seconds: float = 60.0,
    minimum_number_of_calls: int = 10,
    failure_rate_threshold: float = 0.5,
    slow_call_duration_threshold: float = 1.0,
    slow_call_rate_threshold: float = 0.5,
    permitted_number_of_calls_in_half_open_state: int = 3,
    wait_duration_in_open_state: float = 30.0,
) -> CircuitBreakerConfig:
    return CircuitBreakerConfig(
        window_seconds=window_seconds,
        minimum_number_of_calls=minimum_number_of_calls,
        failure_rate_threshold=failure_rate_threshold,
        slow_call_duration_threshold=slow_call_duration_threshold,
        slow_call_rate_threshold=slow_call_rate_threshold,
        permitted_number_of_calls_in_half_open_state=permitted_number_of_calls_in_half_open_state,
        wait_duration_in_open_state=wait_duration_in_open_state,
    )


def _make_breaker(
    clock: ManualClock,
    **config_kwargs,
) -> CircuitBreaker:
    config = _make_config(**config_kwargs)
    return CircuitBreaker(config=config, clock=clock)


def _run_success(breaker: CircuitBreaker, clock: ManualClock, n: int = 1, duration: float = 0.1) -> None:
    for _ in range(n):
        with breaker.acquire():
            clock.advance(duration)


def _run_failure(breaker: CircuitBreaker, clock: ManualClock, n: int = 1, duration: float = 0.1) -> None:
    for _ in range(n):
        try:
            with breaker.acquire():
                clock.advance(duration)
                raise RuntimeError("boom")
        except RuntimeError:
            pass


def _run_slow(breaker: CircuitBreaker, clock: ManualClock, n: int = 1, duration: float = 2.0) -> None:
    for _ in range(n):
        with breaker.acquire():
            clock.advance(duration)


class TestConfigValidation:
    def test_rejects_negative_window(self):
        with pytest.raises(InvalidConfigError, match="window_seconds must be positive"):
            _make_config(window_seconds=-1)

    def test_rejects_zero_window(self):
        with pytest.raises(InvalidConfigError, match="window_seconds must be positive"):
            _make_config(window_seconds=0)

    def test_rejects_non_positive_min_calls(self):
        with pytest.raises(InvalidConfigError, match="minimum_number_of_calls must be positive"):
            _make_config(minimum_number_of_calls=0)

    def test_rejects_failure_rate_out_of_range(self):
        with pytest.raises(InvalidConfigError, match="failure_rate_threshold must be in"):
            _make_config(failure_rate_threshold=0)
        with pytest.raises(InvalidConfigError, match="failure_rate_threshold must be in"):
            _make_config(failure_rate_threshold=1.5)

    def test_rejects_slow_duration_non_positive(self):
        with pytest.raises(InvalidConfigError, match="slow_call_duration_threshold must be positive"):
            _make_config(slow_call_duration_threshold=0)

    def test_rejects_slow_rate_out_of_range(self):
        with pytest.raises(InvalidConfigError, match="slow_call_rate_threshold must be in"):
            _make_config(slow_call_rate_threshold=0)
        with pytest.raises(InvalidConfigError, match="slow_call_rate_threshold must be in"):
            _make_config(slow_call_rate_threshold=2.0)

    def test_rejects_half_open_permits_non_positive(self):
        with pytest.raises(InvalidConfigError, match="permitted_number_of_calls_in_half_open_state must be positive"):
            _make_config(permitted_number_of_calls_in_half_open_state=0)

    def test_rejects_wait_duration_non_positive(self):
        with pytest.raises(InvalidConfigError, match="wait_duration_in_open_state must be positive"):
            _make_config(wait_duration_in_open_state=0)


class TestInitialState:
    def test_starts_closed(self):
        clock = ManualClock()
        breaker = _make_breaker(clock)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_call_permitted() is True

    def test_initial_state_change_event(self):
        clock = ManualClock(start_time=100.0)
        breaker = _make_breaker(clock)
        event = breaker.last_state_change_event
        assert event is not None
        assert event.previous_state == CircuitState.CLOSED
        assert event.current_state == CircuitState.CLOSED
        assert event.reason == StateChangeReason.INITIALIZED
        assert event.timestamp == 100.0


class TestClosedStateNormalFlow:
    def test_success_calls_stay_closed(self):
        clock = ManualClock()
        breaker = _make_breaker(clock, minimum_number_of_calls=5)
        _run_success(breaker, clock, n=20)
        assert breaker.state == CircuitState.CLOSED

    def test_window_stats_accurate(self):
        clock = ManualClock()
        breaker = _make_breaker(clock, minimum_number_of_calls=10)
        _run_success(breaker, clock, n=7)
        _run_failure(breaker, clock, n=3)

        stats = breaker.get_window_stats()
        assert stats.total_count == 10
        assert stats.success_count == 7
        assert stats.failure_count == 3
        assert stats.failure_rate == 0.3


class TestMinimumCallsBoundary:
    def test_below_min_calls_no_trip(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
        )
        _run_failure(breaker, clock, n=5)
        assert breaker.state == CircuitState.CLOSED

    def test_just_at_min_calls_trips_on_failure_rate(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
        )
        _run_success(breaker, clock, n=5)
        _run_failure(breaker, clock, n=5)
        assert breaker.state == CircuitState.OPEN
        event = breaker.last_state_change_event
        assert event.reason == StateChangeReason.FAILURE_RATE_THRESHOLD_EXCEEDED


class TestFailureRateTripping:
    def test_failure_rate_exceeded_trips_open(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
        )
        _run_success(breaker, clock, n=4)
        _run_failure(breaker, clock, n=6)
        assert breaker.state == CircuitState.OPEN

    def test_failure_rate_below_threshold_stays_closed(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.6,
        )
        _run_success(breaker, clock, n=5)
        _run_failure(breaker, clock, n=5)
        assert breaker.state == CircuitState.CLOSED


class TestSlowCallTripping:
    def test_slow_call_rate_exceeded_trips_open(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            slow_call_duration_threshold=1.0,
            slow_call_rate_threshold=0.5,
            failure_rate_threshold=0.99,
        )
        _run_success(breaker, clock, n=5, duration=0.1)
        _run_slow(breaker, clock, n=5, duration=2.0)
        assert breaker.state == CircuitState.OPEN
        event = breaker.last_state_change_event
        assert event.reason == StateChangeReason.SLOW_CALL_RATE_THRESHOLD_EXCEEDED

    def test_slow_call_below_threshold_stays_closed(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            slow_call_duration_threshold=1.0,
            slow_call_rate_threshold=0.6,
            failure_rate_threshold=0.99,
        )
        _run_success(breaker, clock, n=5, duration=0.1)
        _run_slow(breaker, clock, n=5, duration=2.0)
        assert breaker.state == CircuitState.CLOSED


class TestOpenStateFastRejection:
    def test_open_state_denies_permission(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            wait_duration_in_open_state=30.0,
        )
        _run_failure(breaker, clock, n=5)
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_call_permitted() is False

    def test_open_state_raises_on_acquire(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            wait_duration_in_open_state=30.0,
        )
        _run_failure(breaker, clock, n=5)
        with pytest.raises(CircuitBreakerOpenError):
            with breaker.acquire():
                pass


class TestCooldownAndHalfOpenTransition:
    def test_stays_open_before_cooldown(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            wait_duration_in_open_state=30.0,
        )
        _run_failure(breaker, clock, n=5)
        clock.advance(29.0)
        assert breaker.state == CircuitState.OPEN

    def test_transitions_to_half_open_after_cooldown(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            wait_duration_in_open_state=30.0,
        )
        _run_failure(breaker, clock, n=5)
        clock.advance(30.0)
        assert breaker.state == CircuitState.HALF_OPEN
        event = breaker.last_state_change_event
        assert event.reason == StateChangeReason.COOLDOWN_COMPLETE
        assert event.previous_state == CircuitState.OPEN
        assert event.current_state == CircuitState.HALF_OPEN

    def test_exact_cooldown_boundary(self):
        clock = ManualClock(start_time=0.0)
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            wait_duration_in_open_state=10.0,
        )
        _run_failure(breaker, clock, n=5)
        open_time = breaker.last_state_change_event.timestamp
        clock.set(open_time + 10.0)
        assert breaker.state == CircuitState.HALF_OPEN


class TestHalfOpenProbesAndRecovery:
    def test_half_open_allows_limited_probes(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            permitted_number_of_calls_in_half_open_state=3,
            wait_duration_in_open_state=10.0,
        )
        _run_failure(breaker, clock, n=5)
        clock.advance(10.0)
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.is_call_permitted() is True
        _run_success(breaker, clock, n=1)
        assert breaker.is_call_permitted() is True
        _run_success(breaker, clock, n=1)
        assert breaker.is_call_permitted() is True
        _run_success(breaker, clock, n=1)
        assert breaker.state == CircuitState.CLOSED
        event = breaker.last_state_change_event
        assert event.reason == StateChangeReason.HALF_OPEN_SUCCESS

    def test_half_open_failure_reopens(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            permitted_number_of_calls_in_half_open_state=3,
            wait_duration_in_open_state=10.0,
        )
        _run_failure(breaker, clock, n=5)
        clock.advance(10.0)
        assert breaker.state == CircuitState.HALF_OPEN
        _run_success(breaker, clock, n=1)
        _run_failure(breaker, clock, n=1)
        assert breaker.state == CircuitState.OPEN
        event = breaker.last_state_change_event
        assert event.reason == StateChangeReason.HALF_OPEN_FAILURE

    def test_half_open_slow_call_reopens(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            slow_call_duration_threshold=1.0,
            permitted_number_of_calls_in_half_open_state=3,
            wait_duration_in_open_state=10.0,
        )
        _run_failure(breaker, clock, n=5)
        clock.advance(10.0)
        assert breaker.state == CircuitState.HALF_OPEN
        _run_slow(breaker, clock, n=1, duration=2.0)
        assert breaker.state == CircuitState.OPEN
        event = breaker.last_state_change_event
        assert event.reason == StateChangeReason.HALF_OPEN_FAILURE

    def test_half_open_denies_extra_probes(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            permitted_number_of_calls_in_half_open_state=2,
            wait_duration_in_open_state=10.0,
        )
        _run_failure(breaker, clock, n=5)
        clock.advance(10.0)
        _run_success(breaker, clock, n=2, duration=0.1)
        assert breaker.state == CircuitState.CLOSED


class TestSlidingWindowExpiry:
    def test_old_calls_expire(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            window_seconds=60.0,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
        )
        _run_success(breaker, clock, n=5, duration=0.1)
        _run_failure(breaker, clock, n=5, duration=0.1)
        assert breaker.state == CircuitState.OPEN

    def test_expired_failures_no_longer_count(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            window_seconds=10.0,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
            wait_duration_in_open_state=100.0,
        )
        _run_success(breaker, clock, n=4, duration=0.1)
        _run_failure(breaker, clock, n=4, duration=0.1)
        assert breaker.state == CircuitState.CLOSED
        clock.advance(15.0)
        _run_success(breaker, clock, n=4, duration=0.1)
        _run_failure(breaker, clock, n=4, duration=0.1)
        assert breaker.state == CircuitState.CLOSED


class TestClockBackward:
    def test_clock_going_backward_clears_state(self):
        clock = ManualClock(start_time=100.0)
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=5,
            failure_rate_threshold=0.5,
            wait_duration_in_open_state=30.0,
        )
        _run_success(breaker, clock, n=3)
        _run_failure(breaker, clock, n=3)
        clock.set(0.0)
        stats = breaker.get_window_stats()
        assert stats.total_count == 0


class TestFullFlowRecovery:
    def test_closed_open_halfopen_closed_cycle(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            window_seconds=60.0,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
            permitted_number_of_calls_in_half_open_state=2,
            wait_duration_in_open_state=30.0,
        )
        assert breaker.state == CircuitState.CLOSED
        _run_success(breaker, clock, n=4)
        _run_failure(breaker, clock, n=6)
        assert breaker.state == CircuitState.OPEN

        clock.advance(30.0)
        assert breaker.state == CircuitState.HALF_OPEN

        _run_success(breaker, clock, n=2)
        assert breaker.state == CircuitState.CLOSED
        event = breaker.last_state_change_event
        assert event.reason == StateChangeReason.HALF_OPEN_SUCCESS

    def test_closed_open_halfopen_open_retry(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            window_seconds=60.0,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
            permitted_number_of_calls_in_half_open_state=2,
            wait_duration_in_open_state=30.0,
        )
        _run_success(breaker, clock, n=4)
        _run_failure(breaker, clock, n=6)
        assert breaker.state == CircuitState.OPEN

        clock.advance(30.0)
        assert breaker.state == CircuitState.HALF_OPEN
        _run_failure(breaker, clock, n=1)
        assert breaker.state == CircuitState.OPEN

        clock.advance(30.0)
        assert breaker.state == CircuitState.HALF_OPEN
        _run_success(breaker, clock, n=2)
        assert breaker.state == CircuitState.CLOSED


class TestThresholdExactly:
    def test_failure_rate_exactly_at_threshold(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            failure_rate_threshold=0.5,
        )
        _run_success(breaker, clock, n=5)
        _run_failure(breaker, clock, n=5)
        stats = breaker.get_window_stats()
        assert stats.failure_rate == 0.5
        assert breaker.state == CircuitState.OPEN

    def test_slow_rate_exactly_at_threshold(self):
        clock = ManualClock()
        breaker = _make_breaker(
            clock,
            minimum_number_of_calls=10,
            slow_call_duration_threshold=1.0,
            slow_call_rate_threshold=0.5,
            failure_rate_threshold=0.99,
        )
        _run_success(breaker, clock, n=5, duration=0.1)
        _run_slow(breaker, clock, n=5, duration=2.0)
        stats = breaker.get_window_stats()
        assert stats.slow_call_rate == 0.5
        assert breaker.state == CircuitState.OPEN
