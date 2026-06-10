from __future__ import annotations

import pytest

from solocoder_py.notification_fanout import (
    BackoffType,
    ChannelConfig,
    ChannelDeliveryStatus,
    ChannelResult,
    FanoutResult,
    Notification,
    InvalidChannelConfigError,
)


class TestNotification:
    def test_basic_notification(self):
        n = Notification(
            notification_id="n1",
            title="t",
            content="c",
            recipient="u1",
        )
        assert n.notification_id == "n1"
        assert n.title == "t"
        assert n.content == "c"
        assert n.recipient == "u1"
        assert n.metadata == {}

    def test_notification_with_metadata(self):
        n = Notification(
            notification_id="n2",
            title="t",
            content="c",
            recipient="u2",
            metadata={"k": "v"},
        )
        assert n.metadata == {"k": "v"}


class TestChannelConfigValidation:
    def test_default_config_is_valid(self):
        cfg = ChannelConfig(channel_name="email")
        assert cfg.channel_name == "email"
        assert cfg.timeout == 5.0
        assert cfg.max_attempts == 3
        assert cfg.backoff_type == BackoffType.EXPONENTIAL

    def test_empty_channel_name_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="")

    def test_whitespace_channel_name_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="   ")

    def test_non_positive_timeout_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", timeout=0)
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", timeout=-1)

    def test_max_attempts_less_than_one_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", max_attempts=0)
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", max_attempts=-1)

    def test_invalid_backoff_type_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            cfg = ChannelConfig(channel_name="x")
            cfg.backoff_type = "invalid"
            cfg.validate()

    def test_non_positive_initial_delay_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", initial_delay=0)

    def test_backoff_multiplier_less_than_one_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", backoff_multiplier=0.5)

    def test_non_positive_max_delay_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", max_delay=0)

    def test_max_delay_less_than_initial_delay_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", initial_delay=5.0, max_delay=2.0)

    def test_non_positive_fixed_interval_rejected(self):
        with pytest.raises(InvalidChannelConfigError):
            ChannelConfig(channel_name="x", fixed_interval=0)

    def test_max_attempts_one_is_allowed(self):
        cfg = ChannelConfig(channel_name="x", max_attempts=1)
        assert cfg.max_attempts == 1


class TestChannelConfigDelayCalculation:
    def test_first_attempt_no_delay(self):
        cfg = ChannelConfig(channel_name="x", initial_delay=5.0)
        assert cfg.calculate_delay(1) == 0.0

    def test_attempt_number_less_than_one_rejected(self):
        cfg = ChannelConfig(channel_name="x")
        with pytest.raises(ValueError):
            cfg.calculate_delay(0)

    def test_exponential_backoff_sequence(self):
        cfg = ChannelConfig(
            channel_name="x",
            backoff_type=BackoffType.EXPONENTIAL,
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=100.0,
        )
        assert cfg.calculate_delay(1) == 0.0
        assert cfg.calculate_delay(2) == 1.0
        assert cfg.calculate_delay(3) == 2.0
        assert cfg.calculate_delay(4) == 4.0
        assert cfg.calculate_delay(5) == 8.0

    def test_exponential_backoff_capped_at_max_delay(self):
        cfg = ChannelConfig(
            channel_name="x",
            backoff_type=BackoffType.EXPONENTIAL,
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=5.0,
        )
        assert cfg.calculate_delay(2) == 1.0
        assert cfg.calculate_delay(3) == 2.0
        assert cfg.calculate_delay(4) == 4.0
        assert cfg.calculate_delay(5) == 5.0
        assert cfg.calculate_delay(6) == 5.0
        assert cfg.calculate_delay(10) == 5.0

    def test_fixed_interval_backoff(self):
        cfg = ChannelConfig(
            channel_name="x",
            backoff_type=BackoffType.FIXED,
            fixed_interval=3.0,
        )
        assert cfg.calculate_delay(1) == 0.0
        assert cfg.calculate_delay(2) == 3.0
        assert cfg.calculate_delay(3) == 3.0
        assert cfg.calculate_delay(10) == 3.0


class TestChannelResult:
    def test_succeeded_property(self):
        r = ChannelResult(
            channel_name="email",
            status=ChannelDeliveryStatus.SUCCESS,
            attempts=1,
        )
        assert r.succeeded is True
        assert r.failed is False

    def test_failed_property(self):
        r_fail = ChannelResult(
            channel_name="x", status=ChannelDeliveryStatus.FAILED, attempts=3
        )
        r_to = ChannelResult(
            channel_name="y", status=ChannelDeliveryStatus.TIMEOUT, attempts=3
        )
        assert r_fail.failed is True
        assert r_to.failed is True
        assert r_fail.succeeded is False
        assert r_to.succeeded is False


class TestFanoutResultAggregation:
    def _make_result(self, name: str, status: ChannelDeliveryStatus, attempts: int = 1):
        return ChannelResult(channel_name=name, status=status, attempts=attempts)

    def test_all_succeeded(self):
        fr = FanoutResult(
            notification_id="n1",
            channel_results={
                "email": self._make_result("email", ChannelDeliveryStatus.SUCCESS),
                "sms": self._make_result("sms", ChannelDeliveryStatus.SUCCESS),
            },
        )
        assert fr.all_succeeded is True
        assert fr.any_failed is False
        assert fr.succeeded_count == 2
        assert fr.failed_count == 0
        assert fr.channel_count == 2

    def test_partial_failure(self):
        fr = FanoutResult(
            notification_id="n1",
            channel_results={
                "email": self._make_result("email", ChannelDeliveryStatus.SUCCESS),
                "sms": self._make_result("sms", ChannelDeliveryStatus.FAILED),
            },
        )
        assert fr.all_succeeded is False
        assert fr.any_failed is True
        assert fr.succeeded_count == 1
        assert fr.failed_count == 1

    def test_all_failed(self):
        fr = FanoutResult(
            notification_id="n1",
            channel_results={
                "email": self._make_result("email", ChannelDeliveryStatus.TIMEOUT),
                "sms": self._make_result("sms", ChannelDeliveryStatus.FAILED),
            },
        )
        assert fr.all_succeeded is False
        assert fr.any_failed is True
        assert fr.failed_count == 2

    def test_summary_structure(self):
        fr = FanoutResult(
            notification_id="n1",
            channel_results={
                "email": self._make_result("email", ChannelDeliveryStatus.SUCCESS),
                "sms": ChannelResult(
                    channel_name="sms",
                    status=ChannelDeliveryStatus.FAILED,
                    attempts=3,
                    final_error=RuntimeError("boom"),
                ),
            },
            total_duration=1.5,
        )
        s = fr.summary()
        assert s["notification_id"] == "n1"
        assert s["channel_count"] == 2
        assert s["succeeded_count"] == 1
        assert s["failed_count"] == 1
        assert s["all_succeeded"] is False
        assert s["total_duration"] == 1.5
        assert s["channels"]["email"]["status"] == "success"
        assert s["channels"]["sms"]["status"] == "failed"
        assert s["channels"]["sms"]["attempts"] == 3
        assert "boom" in s["channels"]["sms"]["error"]
        assert s["channels"]["email"]["error"] is None
