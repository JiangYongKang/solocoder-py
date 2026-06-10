from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.notification_fanout import (
    BackoffType,
    ChannelConfig,
    ChannelDeliveryStatus,
    ChannelTimeoutError,
    FanoutEngine,
    FanoutExecutionError,
    InMemoryChannel,
    InvalidChannelConfigError,
    Notification,
    UnknownChannelError,
)


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._t

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot sleep for negative seconds")
        with self._lock:
            self._t += seconds


def _notice(nid: str = "n1") -> Notification:
    return Notification(
        notification_id=nid, title="Hello", content="World", recipient="user-1"
    )


class TestEngineRegistration:
    def test_register_and_list_channels(self):
        engine = FanoutEngine()
        ch = InMemoryChannel("email")
        engine.register_channel("email", ch)
        assert "email" in engine.registered_channels

    def test_get_channel(self):
        engine = FanoutEngine()
        ch = InMemoryChannel("email")
        engine.register_channel("email", ch)
        assert engine.get_channel("email") is ch

    def test_get_unknown_channel_raises(self):
        engine = FanoutEngine()
        with pytest.raises(UnknownChannelError) as exc:
            engine.get_channel("missing")
        assert exc.value.channel_name == "missing"

    def test_get_unknown_config_raises(self):
        engine = FanoutEngine()
        with pytest.raises(UnknownChannelError):
            engine.get_channel_config("missing")

    def test_set_config_on_unknown_channel_raises(self):
        engine = FanoutEngine()
        cfg = ChannelConfig(channel_name="x")
        with pytest.raises(UnknownChannelError):
            engine.set_channel_config("x", cfg)

    def test_set_and_get_config(self):
        engine = FanoutEngine()
        engine.register_channel("email", InMemoryChannel("email"))
        new_cfg = ChannelConfig(channel_name="email", timeout=10.0, max_attempts=5)
        engine.set_channel_config("email", new_cfg)
        assert engine.get_channel_config("email").timeout == 10.0
        assert engine.get_channel_config("email").max_attempts == 5

    def test_constructor_channels_arg(self):
        ch = InMemoryChannel("email")
        engine = FanoutEngine(channels={"email": ch})
        assert "email" in engine.registered_channels

    def test_constructor_channels_and_configs(self):
        ch = InMemoryChannel("email")
        cfg = ChannelConfig(channel_name="email", timeout=7.0)
        engine = FanoutEngine(channels={"email": ch}, channel_configs={"email": cfg})
        assert engine.get_channel_config("email").timeout == 7.0


class TestFanoutNormalFlow:
    def test_single_channel_success(self):
        ch = InMemoryChannel("email")
        engine = FanoutEngine(channels={"email": ch})
        notice = _notice()
        result = engine.fanout(notice)
        assert result.notification_id == "n1"
        assert result.channel_count == 1
        assert result.all_succeeded is True
        assert result.channel_results["email"].status == ChannelDeliveryStatus.SUCCESS
        assert result.channel_results["email"].attempts == 1
        assert ch.delivered_count == 1

    def test_three_channels_all_success_parallel(self):
        email = InMemoryChannel("email")
        sms = InMemoryChannel("sms")
        inapp = InMemoryChannel("in_app")

        email.set_delay(0.01)
        sms.set_delay(0.01)
        inapp.set_delay(0.01)

        engine = FanoutEngine(channels={
            "email": email, "sms": sms, "in_app": inapp,
        })

        start = time.monotonic()
        result = engine.fanout(_notice())
        elapsed = time.monotonic() - start

        assert result.all_succeeded is True
        assert result.channel_count == 3
        assert email.delivered_count == 1
        assert sms.delivered_count == 1
        assert inapp.delivered_count == 1

        assert elapsed < 0.08, (
            "并行执行应接近单渠道耗时，实际耗时过长"
        )

    def test_target_channels_subset(self):
        engine = FanoutEngine(channels={
            "email": InMemoryChannel("email"),
            "sms": InMemoryChannel("sms"),
            "in_app": InMemoryChannel("in_app"),
        })
        result = engine.fanout(_notice(), target_channels=["email", "sms"])
        assert result.channel_count == 2
        assert set(result.channel_results.keys()) == {"email", "sms"}


class TestFanoutRetryBackoff:
    def test_single_channel_retry_then_succeeds(self):
        clock = FakeClock()
        ch = InMemoryChannel("email")
        ch.set_fail_next_n(2)
        cfg = ChannelConfig(
            channel_name="email",
            timeout=1.0,
            max_attempts=3,
            backoff_type=BackoffType.EXPONENTIAL,
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
        )
        engine = FanoutEngine(
            channels={"email": ch},
            channel_configs={"email": cfg},
            time_provider=clock.now,
            sleeper=clock.sleep,
        )
        result = engine.fanout(_notice())
        r = result.channel_results["email"]
        assert r.status == ChannelDeliveryStatus.SUCCESS
        assert r.attempts == 3
        assert len(r.attempts_detail) == 3
        assert r.attempts_detail[0].success is False
        assert r.attempts_detail[1].success is False
        assert r.attempts_detail[2].success is True
        assert ch.delivered_count == 1

    def test_fixed_interval_backoff(self):
        clock = FakeClock()
        ch = InMemoryChannel("sms")
        ch.set_fail_next_n(3)
        cfg = ChannelConfig(
            channel_name="sms",
            max_attempts=4,
            backoff_type=BackoffType.FIXED,
            fixed_interval=2.0,
        )
        engine = FanoutEngine(
            channels={"sms": ch},
            channel_configs={"sms": cfg},
            time_provider=clock.now,
            sleeper=clock.sleep,
        )
        result = engine.fanout(_notice())
        r = result.channel_results["sms"]
        assert r.status == ChannelDeliveryStatus.SUCCESS
        assert r.attempts == 4
        assert r.total_duration >= 6.0

    def test_exponential_backoff_delays(self):
        clock = FakeClock()
        ch = InMemoryChannel("email")
        ch.set_fail_next_n(3)
        cfg = ChannelConfig(
            channel_name="email",
            max_attempts=4,
            backoff_type=BackoffType.EXPONENTIAL,
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
        )
        engine = FanoutEngine(
            channels={"email": ch},
            channel_configs={"email": cfg},
            time_provider=clock.now,
            sleeper=clock.sleep,
        )
        result = engine.fanout(_notice())
        r = result.channel_results["email"]
        assert r.attempts == 4
        assert r.total_duration >= 1.0 + 2.0 + 4.0


class TestFanoutFailureScenarios:
    def test_single_channel_all_attempts_fail(self):
        clock = FakeClock()
        ch = InMemoryChannel("email")
        ch.set_fail_next_n(100)
        cfg = ChannelConfig(channel_name="email", max_attempts=3)
        engine = FanoutEngine(
            channels={"email": ch},
            channel_configs={"email": cfg},
            time_provider=clock.now,
            sleeper=clock.sleep,
        )
        result = engine.fanout(_notice())
        r = result.channel_results["email"]
        assert r.status == ChannelDeliveryStatus.FAILED
        assert r.attempts == 3
        assert r.failed is True
        assert r.final_error is not None
        assert all(not a.success for a in r.attempts_detail)
        assert ch.delivered_count == 0

    def test_all_channels_simultaneously_fail(self):
        clock = FakeClock()
        ch1 = InMemoryChannel("email")
        ch2 = InMemoryChannel("sms")
        ch3 = InMemoryChannel("in_app")
        ch1.set_fail_next_n(100)
        ch2.set_fail_next_n(100)
        ch3.set_fail_next_n(100)
        engine = FanoutEngine(
            channels={"email": ch1, "sms": ch2, "in_app": ch3},
            channel_configs={
                "email": ChannelConfig(channel_name="email", max_attempts=2),
                "sms": ChannelConfig(channel_name="sms", max_attempts=2),
                "in_app": ChannelConfig(channel_name="in_app", max_attempts=2),
            },
            time_provider=clock.now,
            sleeper=clock.sleep,
        )
        result = engine.fanout(_notice())
        assert result.all_succeeded is False
        assert result.any_failed is True
        assert result.failed_count == 3
        assert result.succeeded_count == 0
        for name in ("email", "sms", "in_app"):
            assert result.channel_results[name].status == ChannelDeliveryStatus.FAILED
            assert result.channel_results[name].attempts == 2

    def test_mixed_success_and_failure(self):
        clock = FakeClock()
        good = InMemoryChannel("email")
        bad = InMemoryChannel("sms")
        bad.set_fail_next_n(100)
        engine = FanoutEngine(
            channels={"email": good, "sms": bad},
            channel_configs={
                "email": ChannelConfig(channel_name="email", max_attempts=2),
                "sms": ChannelConfig(channel_name="sms", max_attempts=2),
            },
            time_provider=clock.now,
            sleeper=clock.sleep,
        )
        result = engine.fanout(_notice())
        assert result.channel_results["email"].succeeded is True
        assert result.channel_results["sms"].failed is True
        assert result.succeeded_count == 1
        assert result.failed_count == 1


class TestTimeoutBehavior:
    def test_channel_timeout(self):
        ch = InMemoryChannel("slow")
        ch.set_delay(0.5)
        cfg = ChannelConfig(channel_name="slow", timeout=0.05, max_attempts=1)
        engine = FanoutEngine(
            channels={"slow": ch},
            channel_configs={"slow": cfg},
        )
        result = engine.fanout(_notice())
        r = result.channel_results["slow"]
        assert r.status == ChannelDeliveryStatus.TIMEOUT
        assert isinstance(r.final_error, ChannelTimeoutError)
        assert r.final_error.channel_name == "slow"
        assert r.final_error.timeout == 0.05

    def test_timeout_then_retry(self):
        ch = InMemoryChannel("flaky")
        ch.set_delay(0.5)
        cfg = ChannelConfig(
            channel_name="flaky", timeout=0.05, max_attempts=2
        )
        engine = FanoutEngine(
            channels={"flaky": ch},
            channel_configs={"flaky": cfg},
        )
        result = engine.fanout(_notice())
        r = result.channel_results["flaky"]
        assert r.status == ChannelDeliveryStatus.TIMEOUT
        assert r.attempts == 2


class TestEdgeCases:
    def test_only_one_channel(self):
        engine = FanoutEngine(channels={"email": InMemoryChannel("email")})
        result = engine.fanout(_notice())
        assert result.channel_count == 1
        assert result.all_succeeded is True

    def test_max_attempts_one_no_retries(self):
        ch = InMemoryChannel("email")
        ch.set_fail_next_n(10)
        cfg = ChannelConfig(channel_name="email", max_attempts=1)
        engine = FanoutEngine(
            channels={"email": ch},
            channel_configs={"email": cfg},
        )
        result = engine.fanout(_notice())
        assert result.channel_results["email"].attempts == 1
        assert result.channel_results["email"].status == ChannelDeliveryStatus.FAILED

    def test_fanout_to_unknown_channel_raises(self):
        engine = FanoutEngine(channels={"email": InMemoryChannel("email")})
        with pytest.raises(UnknownChannelError):
            engine.fanout(_notice(), target_channels=["email", "sms"])

    def test_fanout_with_no_targets_raises(self):
        engine = FanoutEngine()
        with pytest.raises(FanoutExecutionError):
            engine.fanout(_notice(), target_channels=[])

    def test_fanout_defaults_to_all_registered(self):
        ch1 = InMemoryChannel("email")
        ch2 = InMemoryChannel("sms")
        engine = FanoutEngine(channels={"email": ch1, "sms": ch2})
        result = engine.fanout(_notice())
        assert result.channel_count == 2
        assert ch1.delivered_count == 1
        assert ch2.delivered_count == 1


class TestResultAggregation:
    def test_summary_contains_all_channels(self):
        ch1 = InMemoryChannel("email")
        ch2 = InMemoryChannel("sms")
        ch2.set_fail_next_n(100)
        engine = FanoutEngine(
            channels={"email": ch1, "sms": ch2},
            channel_configs={
                "email": ChannelConfig(channel_name="email", max_attempts=1),
                "sms": ChannelConfig(channel_name="sms", max_attempts=1),
            },
        )
        result = engine.fanout(_notice())
        s = result.summary()
        assert s["channel_count"] == 2
        assert s["succeeded_count"] == 1
        assert s["failed_count"] == 1
        assert s["channels"]["email"]["status"] == "success"
        assert s["channels"]["sms"]["status"] == "failed"
        assert s["channels"]["sms"]["error"] is not None
        assert s["total_duration"] >= 0.0

    def test_attempts_detail_records_error(self):
        ch = InMemoryChannel("email")
        ch.set_fail_next_n(100)
        cfg = ChannelConfig(channel_name="email", max_attempts=2)
        engine = FanoutEngine(
            channels={"email": ch},
            channel_configs={"email": cfg},
        )
        result = engine.fanout(_notice())
        attempts = result.channel_results["email"].attempts_detail
        assert len(attempts) == 2
        for a in attempts:
            assert a.success is False
            assert a.error is not None
            assert a.duration >= 0.0
            assert a.attempt_number >= 1


class TestChannelConfigNameValidation:
    def test_register_channel_with_mismatched_config_name_rejected(self):
        engine = FanoutEngine()
        ch = InMemoryChannel("email")
        bad_cfg = ChannelConfig(channel_name="sms", timeout=5.0)
        with pytest.raises(InvalidChannelConfigError) as exc:
            engine.register_channel("email", ch, bad_cfg)
        assert "sms" in str(exc.value)
        assert "email" in str(exc.value)
        assert "email" not in engine.registered_channels

    def test_set_channel_config_with_mismatched_name_rejected(self):
        engine = FanoutEngine()
        engine.register_channel("email", InMemoryChannel("email"))
        bad_cfg = ChannelConfig(channel_name="sms", timeout=5.0)
        with pytest.raises(InvalidChannelConfigError) as exc:
            engine.set_channel_config("email", bad_cfg)
        assert "sms" in str(exc.value)
        assert "email" in str(exc.value)

    def test_register_channel_with_matching_config_name_accepted(self):
        engine = FanoutEngine()
        ch = InMemoryChannel("email")
        good_cfg = ChannelConfig(channel_name="email", timeout=7.0, max_attempts=5)
        engine.register_channel("email", ch, good_cfg)
        assert "email" in engine.registered_channels
        assert engine.get_channel_config("email").timeout == 7.0

    def test_constructor_rejects_mismatched_config_names(self):
        ch = InMemoryChannel("email")
        bad_cfg = ChannelConfig(channel_name="sms")
        with pytest.raises(InvalidChannelConfigError):
            FanoutEngine(channels={"email": ch}, channel_configs={"email": bad_cfg})


class TestTimeoutDoesNotBlock:
    def test_permanently_blocking_channel_returns_on_timeout(self):
        ch = InMemoryChannel("stuck")
        ch.set_delay(300)
        cfg = ChannelConfig(channel_name="stuck", timeout=0.05, max_attempts=1)
        engine = FanoutEngine(
            channels={"stuck": ch},
            channel_configs={"stuck": cfg},
        )

        start = time.monotonic()
        result = engine.fanout(_notice())
        elapsed = time.monotonic() - start

        r = result.channel_results["stuck"]
        assert r.status == ChannelDeliveryStatus.TIMEOUT
        assert isinstance(r.final_error, ChannelTimeoutError)
        assert elapsed < 1.0, (
            f"超时后应立即返回，不应等待底层线程，实际耗时 {elapsed:.2f}s"
        )

    def test_long_running_channel_mixed_with_fast_channel_parallel(self):
        slow = InMemoryChannel("slow")
        slow.set_delay(300)
        fast = InMemoryChannel("fast")

        engine = FanoutEngine(
            channels={"slow": slow, "fast": fast},
            channel_configs={
                "slow": ChannelConfig(channel_name="slow", timeout=0.05, max_attempts=1),
                "fast": ChannelConfig(channel_name="fast", max_attempts=1),
            },
        )

        start = time.monotonic()
        result = engine.fanout(_notice())
        elapsed = time.monotonic() - start

        assert result.channel_results["slow"].status == ChannelDeliveryStatus.TIMEOUT
        assert result.channel_results["fast"].status == ChannelDeliveryStatus.SUCCESS
        assert fast.delivered_count == 1
        assert elapsed < 1.0, (
            f"慢渠道超时不应阻塞整体结果，实际耗时 {elapsed:.2f}s"
        )


class TestParallelismIndependentOfWorkerLimit:
    def test_many_channels_not_blocked_by_max_workers(self):
        channels = {}
        configs = {}
        for i in range(10):
            name = f"ch-{i}"
            ch = InMemoryChannel(name)
            ch.set_delay(0.05)
            channels[name] = ch
            configs[name] = ChannelConfig(channel_name=name, max_attempts=1)

        engine = FanoutEngine(
            channels=channels,
            channel_configs=configs,
            max_workers=2,
        )

        start = time.monotonic()
        result = engine.fanout(_notice())
        elapsed = time.monotonic() - start

        assert result.channel_count == 10
        assert result.all_succeeded is True
        for i in range(10):
            assert channels[f"ch-{i}"].delivered_count == 1

        assert elapsed < 0.5, (
            f"各渠道应独立并行，不受 max_workers 限制，实际耗时 {elapsed:.2f}s"
        )

    def test_slow_does_not_block_others_despite_small_max_workers(self):
        slow = InMemoryChannel("slow")
        slow.set_delay(0.2)
        fast1 = InMemoryChannel("fast1")
        fast2 = InMemoryChannel("fast2")

        engine = FanoutEngine(
            channels={"slow": slow, "fast1": fast1, "fast2": fast2},
            channel_configs={
                "slow": ChannelConfig(channel_name="slow", max_attempts=1),
                "fast1": ChannelConfig(channel_name="fast1", max_attempts=1),
                "fast2": ChannelConfig(channel_name="fast2", max_attempts=1),
            },
            max_workers=1,
        )

        start = time.monotonic()
        result = engine.fanout(_notice())
        elapsed = time.monotonic() - start

        assert result.all_succeeded is True
        assert slow.delivered_count == 1
        assert fast1.delivered_count == 1
        assert fast2.delivered_count == 1
        assert elapsed < 0.4, (
            f"各渠道应并行执行，慢渠道不应阻塞快渠道，实际耗时 {elapsed:.2f}s"
        )
