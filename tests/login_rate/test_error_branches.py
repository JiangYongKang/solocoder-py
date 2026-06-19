from __future__ import annotations

import pytest

from solocoder_py.login_rate import (
    AccountLockedError,
    BackoffActiveError,
    CaptchaRequiredError,
    CaptchaInvalidError,
    InvalidAccountError,
    InvalidIPError,
    LoginRateConfig,
    LoginRateManager,
    ManualClock,
    NoSuchAccountCounterError,
    NoSuchSubnetCounterError,
)


class TestBackoffNoPasswordVerification:
    def test_backoff_does_not_call_password_verifier(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=10,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        call_count = {"n": 0}

        def verifier():
            call_count["n"] += 1
            return True

        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        result = manager.attempt_login("user1", "192.168.1.10", verifier)
        assert result.success is False
        assert isinstance(result.error, BackoffActiveError)
        assert call_count["n"] == 0

    def test_backoff_returns_correct_remaining_time(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=50,
            initial_backoff_seconds=8,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(3.0)
        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert isinstance(result.error, BackoffActiveError)
        assert result.error.remaining_seconds == 5


class TestLockedAccountDirectRejection:
    def test_locked_does_not_call_password_verifier(self):
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

        call_count = {"n": 0}

        def verifier():
            call_count["n"] += 1
            return True

        clock.advance(100.0)
        result = manager.attempt_login("user1", "192.168.1.10", verifier)
        assert result.success is False
        assert isinstance(result.error, AccountLockedError)
        assert call_count["n"] == 0


class TestInvalidAccountRejection:
    def test_empty_account_rejected(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(InvalidAccountError, match="Invalid account"):
            manager.attempt_login("", "192.168.1.10", lambda: True)

    def test_none_account_rejected(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(InvalidAccountError):
            manager.attempt_login(None, "192.168.1.10", lambda: True)

    def test_special_char_account_rejected(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(InvalidAccountError):
            manager.attempt_login("user@name", "192.168.1.10", lambda: True)

        with pytest.raises(InvalidAccountError):
            manager.attempt_login("user name", "192.168.1.10", lambda: True)

        with pytest.raises(InvalidAccountError):
            manager.attempt_login("user/name", "192.168.1.10", lambda: True)

    def test_valid_account_accepted(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        result = manager.attempt_login("user.name_123-test", "192.168.1.10", lambda: True)
        assert result.success is True


class TestInvalidIPRejection:
    def test_empty_ip_rejected(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(InvalidIPError, match="Invalid IP address"):
            manager.attempt_login("user1", "", lambda: True)

    def test_malformed_ip_rejected(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(InvalidIPError):
            manager.attempt_login("user1", "not_an_ip", lambda: True)

        with pytest.raises(InvalidIPError):
            manager.attempt_login("user1", "256.1.1.1", lambda: True)

        with pytest.raises(InvalidIPError):
            manager.attempt_login("user1", "192.168.1", lambda: True)

        with pytest.raises(InvalidIPError):
            manager.attempt_login("user1", "192.168.1.1.1", lambda: True)

    def test_none_ip_rejected(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(InvalidIPError):
            manager.attempt_login("user1", None, lambda: True)


class TestNonexistentCounterAccess:
    def test_get_nonexistent_account_counter_raises(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(NoSuchAccountCounterError, match="No counter exists for account"):
            manager.get_account_failure_count("ghost_user")

    def test_get_nonexistent_subnet_counter_raises(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(NoSuchSubnetCounterError, match="No counter exists for subnet"):
            manager.get_subnet_failure_count("10.0.0.0/24")

    def test_has_account_counter_check(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        assert manager.has_account_counter("user1") is False
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        assert manager.has_account_counter("user1") is True

    def test_has_subnet_counter_check(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        assert manager.has_subnet_counter("192.168.1.0/24") is False
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        assert manager.has_subnet_counter("192.168.1.0/24") is True

    def test_unlock_nonexistent_account_raises(self):
        clock = ManualClock(start_time=0.0)
        manager = LoginRateManager(clock=clock)

        with pytest.raises(NoSuchAccountCounterError):
            manager.unlock_account("ghost_user")


class TestCaptchaRequiredAndInvalid:
    def test_subnet_threshold_requires_captcha(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=2,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )
        manager = LoginRateManager(config=config, clock=clock)

        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("user2", "192.168.1.20", lambda: False)

        result = manager.attempt_login("user3", "192.168.1.30", lambda: True)
        assert result.success is False
        assert isinstance(result.error, CaptchaRequiredError)
        assert result.error.subnet == "192.168.1.0/24"

    def test_invalid_captcha_rejected(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=2,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )

        class TestVerifier:
            def verify(self, account, ip, solution):
                return False

        manager = LoginRateManager(config=config, clock=clock, captcha_verifier=TestVerifier())

        clock.advance(10.0)
        manager.attempt_login("user1", "192.168.1.10", lambda: False)
        clock.advance(10.0)
        manager.attempt_login("user2", "192.168.1.20", lambda: False)

        result = manager.attempt_login(
            "user3",
            "192.168.1.30",
            lambda: True,
            captcha_solution="wrong",
        )
        assert result.success is False
        assert isinstance(result.error, CaptchaInvalidError)

    def test_captcha_not_called_below_threshold(self):
        clock = ManualClock(start_time=0.0)
        config = LoginRateConfig(
            account_lock_threshold=10,
            subnet_captcha_threshold=5,
            initial_backoff_seconds=1,
            max_backoff_seconds=300,
        )

        call_count = {"n": 0}

        class TestVerifier:
            def verify(self, account, ip, solution):
                call_count["n"] += 1
                return True

        manager = LoginRateManager(config=config, clock=clock, captcha_verifier=TestVerifier())
        result = manager.attempt_login("user1", "192.168.1.10", lambda: True)
        assert result.success is True
        assert call_count["n"] == 0


class TestConfigValidation:
    def test_invalid_lock_threshold(self):
        with pytest.raises(ValueError, match="account_lock_threshold must be positive"):
            LoginRateConfig(account_lock_threshold=0)

        with pytest.raises(ValueError, match="account_lock_threshold must be positive"):
            LoginRateConfig(account_lock_threshold=-1)

    def test_invalid_captcha_threshold(self):
        with pytest.raises(ValueError, match="subnet_captcha_threshold must be positive"):
            LoginRateConfig(subnet_captcha_threshold=0)

    def test_invalid_initial_backoff(self):
        with pytest.raises(ValueError, match="initial_backoff_seconds must be positive"):
            LoginRateConfig(initial_backoff_seconds=0)

    def test_invalid_max_backoff(self):
        with pytest.raises(ValueError, match="max_backoff_seconds must be positive"):
            LoginRateConfig(max_backoff_seconds=0)

    def test_initial_exceeds_max(self):
        with pytest.raises(ValueError, match="initial_backoff_seconds cannot exceed max_backoff_seconds"):
            LoginRateConfig(initial_backoff_seconds=100, max_backoff_seconds=50)

    def test_invalid_multiplier(self):
        with pytest.raises(ValueError, match="backoff_multiplier must be greater than 1"):
            LoginRateConfig(backoff_multiplier=1)

        with pytest.raises(ValueError, match="backoff_multiplier must be greater than 1"):
            LoginRateConfig(backoff_multiplier=0)
