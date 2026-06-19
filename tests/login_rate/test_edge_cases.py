from __future__ import annotations

import pytest

from solocoder_py.login_rate import (
    AccountLockedError,
    BackoffActiveError,
    CaptchaRequiredError,
    CaptchaInvalidError,
    LoginRateConfig,
    LoginRateManager,
    ManualClock,
    NoSuchAccountCounterError,
)


class TestBackoffUpperBound:
    def test_backoff_does_not_exceed_max(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=100,
            subnet_captcha_threshold=200,
            initial_backoff_seconds=1,
            max_backoff_seconds=10,
            backoff_multiplier=2,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for failures in range(1, 20):
            backoff = manager.calculate_backoff_for_failures(failures)
            assert backoff <= 10, f"Backoff {backoff} exceeded max 10 for {failures} failures"

    def test_backoff_capped_at_exact_max(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=100,
            subnet_captcha_threshold=200,
            initial_backoff_seconds=1,
            max_backoff_seconds=10,
            backoff_multiplier=2,
        )
        manager = LoginRateManager(config=config, clock=clock)

        assert manager.calculate_backoff_for_failures(1) == 1
        assert manager.calculate_backoff_for_failures(2) == 2
        assert manager.calculate_backoff_for_failures(3) == 4
        assert manager.calculate_backoff_for_failures(4) == 8
        assert manager.calculate_backoff_for_failures(5) == 10
        assert manager.calculate_backoff_for_failures(10) == 10
        assert manager.calculate_backoff_for_failures(100) == 10

    def test_zero_failures_zero_backoff(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=20,
            initial_backoff_seconds=5,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)
        assert manager.calculate_backoff_for_failures(0) == 0


class TestSubnetIndependentAccountCounters:
    def test_same_subnet_different_accounts_separate_counters(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for i in range(5):
            clock.advance(10.0)
            manager.attempt_login("alice", "192.168.1.10", lambda: False)

        for i in range(3):
            clock.advance(10.0)
            manager.attempt_login("bob", "192.168.1.20", lambda: False)

        assert manager.get_account_failure_count("alice") == 5
        assert manager.get_account_failure_count("bob") == 3
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 8

    def test_account_lock_does_not_affect_other_accounts_same_subnet(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=2,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        clock.advance(10.0)
        manager.attempt_login("alice", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("alice", "192.168.1.10", lambda: False)

        assert manager.is_account_locked("alice") is True
        with pytest.raises(NoSuchAccountCounterError, match="不存在该账户的计数器"):
            manager.is_account_locked("bob")

        result = manager.attempt_login("bob", "192.168.1.20", lambda: True)
        assert result.success is True


class TestSuccessfulLoginResetsCounters:
    def test_success_resets_both_account_and_subnet(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        for _ in range(4):
            clock.advance(10.0)
            manager.attempt_login("user1", "192.168.1.10", lambda: False)

        assert manager.get_account_failure_count("user1") == 4
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 4

        clock.advance(10.0)
        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is True
        assert result.account_failures == 0
        assert result.subnet_failures == 0
        assert manager.get_account_failure_count("user1") == 0
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 0

    def test_success_after_partial_backoff_resets_completely(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=10,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(3.0)
        assert manager.get_backoff_seconds("user1") == 7

        clock.advance(7.0)
        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is True
        assert manager.get_backoff_seconds("user1") == 0


class TestAdminUnlock:
    def test_unlock_resets_locked_state(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=2,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)

        assert manager.is_account_locked("user1") is True

        manager.unlock_account("user1")
        assert manager.is_account_locked("user1") is False
        assert manager.get_account_failure_count("user1") == 0

    def test_unlocked_account_can_login_successfully(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=2,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)

        manager.unlock_account("user1")

        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is True

    def test_unlocked_account_can_fail_again(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=2,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)

        manager.unlock_account("user1")

        clock.advance(10.0)
        result1 = manager.attempt_login("user1", "192.168.1.10", lambda: False)
        assert result1.success is False
        assert result1.account_failures == 1
        assert manager.is_account_locked("user1") is False

        clock.advance(10.0)
        result2 = manager.attempt_login("user1", "192.168.1.10", lambda: False)
        assert result2.success is False
        assert result2.account_failures == 2
        assert manager.is_account_locked("user1") is True


class TestCaptchaBypass:
    def test_captcha_allows_locked_account_password_check(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=2,
            subnet_captcha_threshold=3,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )

        class TestVerifier:
            def verify(self, account, ip, solution):
                return solution == "correct"

        manager = LoginRateManager(config=config, clock=clock, captcha_verifier=TestVerifier())

        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        assert manager.is_account_locked("user1") is True
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 2

        clock.advance(10.0)
        manager.attempt_login("user2", "192.168.1.20", lambda: False)
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 3

        result_no_captcha = manager.attempt_login(
            "user1",
            "192.168.1.10",
            lambda: True,
        )
        assert result_no_captcha.success is False
        assert isinstance(result_no_captcha.error, CaptchaRequiredError)

        result_wrong_captcha = manager.attempt_login(
            "user1",
            "192.168.1.10",
            lambda: True,
            captcha_solution="wrong",
        )
        assert result_wrong_captcha.success is False
        assert isinstance(result_wrong_captcha.error, CaptchaInvalidError)

        result_with_captcha = manager.attempt_login(
            "user1",
            "192.168.1.10",
            lambda: True,
            captcha_solution="correct",
        )
        assert result_with_captcha.success is True

    def test_captcha_bypasses_backoff(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=2,
            initial_backoff_seconds=100,
            max_backoff_seconds=300,
        )

        class TestVerifier:
            def verify(self, account, ip, solution):
                return solution == "correct"

        manager = LoginRateManager(config=config, clock=clock, captcha_verifier=TestVerifier())

        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        assert manager.get_backoff_seconds("user1") == 100

        clock.advance(10.0)
        manager.attempt_login("user2", "192.168.1.20", lambda: False)
        assert manager.get_subnet_failure_count("192.168.1.0/24") == 2

        result_no_captcha = manager.attempt_login(
            "user1",
            "192.168.1.10",
            lambda: True,
        )
        assert result_no_captcha.success is False
        assert isinstance(result_no_captcha.error, CaptchaRequiredError)

        result_with_captcha = manager.attempt_login(
            "user1",
            "192.168.1.10",
            lambda: True,
            captcha_solution="correct",
        )
        assert result_with_captcha.success is True
