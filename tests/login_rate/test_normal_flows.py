from __future__ import annotations

import pytest

from solocoder_py.login_rate import (
    AccountLockedError,
    BackoffActiveError,
    LoginRateConfig,
    LoginRateManager,
    ManualClock,
)


class TestLoginFailureCountIncrement:
    def test_single_failure_increments_account_counter(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=5,
            subnet_captcha_threshold=10,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        result = manager.attempt_login("user1", "192.168.1.10", lambda: False)
        assert result.success is False
        assert result.account_failures == 1
        assert result.subnet_failures == 1
        assert manager.get_account_failure_count("user1") == 1

    def test_multiple_failures_increment_both_counters(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=5,
            subnet_captcha_threshold=10,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for i in range(3):
            result = manager.attempt_login("user1", "192.168.1.10", lambda: False)
            assert result.success is False
            assert result.account_failures == i + 1
            assert result.subnet_failures == i + 1
            clock.advance(10.0)

        assert manager.get_account_failure_count("user1") == 3
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 3

    def test_successful_login_resets_counters(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=5,
            subnet_captcha_threshold=10,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for _ in range(3):
            manager.attempt_login("user1", "192.168.1.10", lambda: False)
            clock.advance(10.0)

        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is True
        assert result.account_failures == 0
        assert result.subnet_failures == 0
        assert manager.get_account_failure_count("user1") == 0
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 0


class TestStaircaseBackoff:
    def test_first_failure_backoff_is_initial(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
            backoff_multiplier=2,
        )
        manager = LoginRateManager(config=config, clock=clock)

        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        backoff = manager.calculate_backoff_for_failures(1)
        assert backoff == 1

    def test_second_failure_backoff_doubles(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
            backoff_multiplier=2,
        )
        manager = LoginRateManager(config=config, clock=clock)

        backoff = manager.calculate_backoff_for_failures(2)
        assert backoff == 2

    def test_third_failure_backoff_quadruples(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
            backoff_multiplier=2,
        )
        manager = LoginRateManager(config=config, clock=clock)

        backoff = manager.calculate_backoff_for_failures(3)
        assert backoff == 4

    def test_backoff_with_different_multiplier(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=2,
            max_backoff_seconds=300,
            backoff_multiplier=3,
        )
        manager = LoginRateManager(config=config, clock=clock)

        assert manager.calculate_backoff_for_failures(1) == 2
        assert manager.calculate_backoff_for_failures(2) == 6
        assert manager.calculate_backoff_for_failures(3) == 18

    def test_backoff_active_blocks_login(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=5,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        manager.attempt_login("user1", "192.168.1.10", lambda: False)

        clock.advance(2.0)
        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is False
        assert isinstance(result.error, BackoffActiveError)
        assert result.error.remaining_seconds == 3

    def test_backoff_expires_allows_login(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=5,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        manager.attempt_login("user1", "192.168.1.10", lambda: False)

        clock.advance(5.0)
        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is True


class TestAccountLockThreshold:
    def test_lock_triggers_at_threshold(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=3,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for i in range(3):
            clock.advance(10.0)
            result = manager.attempt_login("user1", "192.168.1.10", lambda: False)
            if i < 2:
                assert result.success is False
                assert result.error is None

        assert manager.is_account_locked("user1") is True

    def test_locked_account_rejected(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=2,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)

        clock.advance(100.0)
        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is False
        assert isinstance(result.error, AccountLockedError)
        assert result.error.account == "user1"


class TestSubnetCounterIndependence:
    def test_different_subnets_have_separate_counters(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for _ in range(3):
            clock.advance(10.0)
            manager.attempt_login("user_a", "192.168.1.10", lambda: False)

        for _ in range(5):
            clock.advance(10.0)
            manager.attempt_login("user_b", "10.0.0.5", lambda: False)

        assert manager.get_subnet_failure_count("192.168.1.0/24") == 3
        assert manager.get_subnet_failure_count("10.0.0.0/24") == 5

    def test_same_subnet_different_accounts_accumulate(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for _ in range(2):
            clock.advance(10.0)
            manager.attempt_login("user1", "192.168.1.10", lambda: False)

        for _ in range(3):
            clock.advance(10.0)
            manager.attempt_login("user2", "192.168.1.20", lambda: False)

        assert manager.get_account_failure_count("user1") == 2
        assert manager.get_account_failure_count("user2") == 3
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 5
