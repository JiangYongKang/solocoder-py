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
    NotificationChannel,
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


class EventControlledChannel(NotificationChannel):
    def __init__(self, name: str) -> None:
        self._name = name
        self._start_event = threading.Event()
        self._release_event = threading.Event()
        self._delivered: list[Notification] = []
        self._fail_next_n = 0
        self._started_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def delivered_count(self) -> int:
        return len(self._delivered)

    @property
    def delivered(self) -> list[Notification]:
        return list(self._delivered)

    @property
    def started_count(self) -> int:
        return self._started_count

    def set_fail_next_n(self, n: int) -> None:
        self._fail_next_n = n

    def wait_until_started(self, timeout: float = 5.0) -> bool:
        return self._start_event.wait(timeout=timeout)

    def release(self) -> None:
        self._release_event.set()

    def reset_events(self) -> None:
        self._start_event.clear()
        self._release_event.clear()

    def deliver(self, notification: Notification) -> None:
        self._started_count += 1
        self._start_event.set()
        self._release_event.wait()
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError(f"Channel '{self._name}' simulated failure")
        self._delivered.append(notification)


class BarrierChannel(NotificationChannel):
    def __init__(self, name: str, barrier: threading.Barrier) -> None:
        self._name = name
        self._barrier = barrier
        self._delivered: list[Notification] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def delivered_count(self) -> int:
        return len(self._delivered)

    def deliver(self, notification: Notification) -> None:
        self._barrier.wait(timeout=5.0)
        self._delivered.append(notification)


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

    def test_three_channels_all_success_parallel_with_barrier(self):
        barrier = threading.Barrier(3, timeout=5.0)
        ch1 = BarrierChannel("email", barrier)
        ch2 = BarrierChannel("sms", barrier)
        ch3 = BarrierChannel("in_app", barrier)

        engine = FanoutEngine(channels={"email": ch1, "sms": ch2, "in_app": ch3})

        result = engine.fanout(_notice())
        assert result.all_succeeded is True
        assert result.channel_count == 3
        assert ch1.delivered_count == 1
        assert ch2.delivered_count == 1
        assert ch3.delivered_count == 1

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
        ch = EventControlledChannel("slow")
        cfg = ChannelConfig(channel_name="slow", timeout=0.1, max_attempts=1)
        engine = FanoutEngine(
            channels={"slow": ch},
            channel_configs={"slow": cfg},
        )

        result = engine.fanout(_notice())
        r = result.channel_results["slow"]
        assert r.status == ChannelDeliveryStatus.TIMEOUT
        assert isinstance(r.final_error, ChannelTimeoutError)
        assert r.final_error.channel_name == "slow"
        assert r.final_error.timeout == 0.1
        ch.release()

    def test_timeout_then_retry(self):
        ch = EventControlledChannel("flaky")
        cfg = ChannelConfig(channel_name="flaky", timeout=0.05, max_attempts=2)
        engine = FanoutEngine(
            channels={"flaky": ch},
            channel_configs={"flaky": cfg},
        )
        result = engine.fanout(_notice())
        r = result.channel_results["flaky"]
        assert r.status == ChannelDeliveryStatus.TIMEOUT
        assert r.attempts == 2
        ch.release()
        ch.release()


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
        ch = EventControlledChannel("stuck")
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
        assert ch.started_count >= 1
        assert elapsed < 2.0
        ch.release()

    def test_blocked_channel_mixed_with_fast_channel_parallel(self):
        slow = EventControlledChannel("slow")
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
        assert slow.started_count >= 1
        assert elapsed < 2.0
        slow.release()


class TestParallelismIndependentOfWorkerLimit:
    def test_ten_channels_parallel_with_barrier_despite_small_max_workers(self):
        barrier = threading.Barrier(10, timeout=5.0)
        channels = {}
        configs = {}
        for i in range(10):
            name = f"ch-{i}"
            channels[name] = BarrierChannel(name, barrier)
            configs[name] = ChannelConfig(channel_name=name, max_attempts=1)

        engine = FanoutEngine(
            channels=channels,
            channel_configs=configs,
            max_workers=2,
        )

        result = engine.fanout(_notice())
        assert result.channel_count == 10
        assert result.all_succeeded is True
        for i in range(10):
            assert channels[f"ch-{i}"].delivered_count == 1

    def test_slow_does_not_block_others_using_barrier(self):
        barrier = threading.Barrier(3, timeout=5.0)
        slow = BarrierChannel("slow", barrier)
        fast1 = BarrierChannel("fast1", barrier)
        fast2 = BarrierChannel("fast2", barrier)

        engine = FanoutEngine(
            channels={"slow": slow, "fast1": fast1, "fast2": fast2},
            channel_configs={
                "slow": ChannelConfig(channel_name="slow", max_attempts=1),
                "fast1": ChannelConfig(channel_name="fast1", max_attempts=1),
                "fast2": ChannelConfig(channel_name="fast2", max_attempts=1),
            },
            max_workers=1,
        )

        result = engine.fanout(_notice())
        assert result.all_succeeded is True
        assert slow.delivered_count == 1
        assert fast1.delivered_count == 1
        assert fast2.delivered_count == 1


class TestDuplicateDeliveryPrevention:
    def test_background_thread_success_does_not_duplicate(self):
        ch = EventControlledChannel("slow-success")
        cfg = ChannelConfig(channel_name="slow-success", timeout=0.05, max_attempts=2)
        engine = FanoutEngine(
            channels={"slow-success": ch},
            channel_configs={"slow-success": cfg},
        )

        fanout_thread = threading.Thread(target=lambda: engine.fanout(_notice()), daemon=True)
        fanout_thread.start()

        assert ch.wait_until_started(timeout=5.0), "投递应已启动"

        fanout_thread.join(timeout=2.0)
        assert not fanout_thread.is_alive(), "fanout 应已在超时后返回"

        assert ch.delivered_count == 0, "后台线程未释放，不应已成功"

        ch.release()

        time.sleep(0.1)

        assert ch.delivered_count == 1, "后台线程释放后仅应成功投递 1 次"

    def test_worker_catches_unexpected_exception_and_still_records_result(self):
        class BrokenChannel(NotificationChannel):
            @property
            def name(self) -> str:
                return "broken"

            def deliver(self, notification: Notification) -> None:
                raise SystemExit("simulated catastrophic exit")

        engine = FanoutEngine(channels={"broken": BrokenChannel()})
        result = engine.fanout(_notice())

        assert "broken" in result.channel_results
        r = result.channel_results["broken"]
        assert r.status == ChannelDeliveryStatus.FAILED
        assert r.final_error is not None

    def test_every_channel_has_result_even_when_one_misbehaves(self):
        class BadChannel(NotificationChannel):
            @property
            def name(self) -> str:
                return "bad"

            def deliver(self, notification: Notification) -> None:
                raise KeyboardInterrupt("oops")

        bad = BadChannel()
        good = InMemoryChannel("good")

        engine = FanoutEngine(channels={"bad": bad, "good": good})
        result = engine.fanout(_notice())

        assert result.channel_count == 2
        assert "bad" in result.channel_results
        assert "good" in result.channel_results
        assert result.channel_results["bad"].failed is True
        assert result.channel_results["good"].succeeded is True
        assert good.delivered_count == 1


class TestLateSuccessRecordedCorrectly:
    def test_background_thread_late_success_captured_in_attempts_detail(self):
        ch = EventControlledChannel("late")
        cfg = ChannelConfig(
            channel_name="late",
            timeout=0.05,
            max_attempts=2,
            backoff_type=BackoffType.FIXED,
            fixed_interval=0.01,
        )
        engine = FanoutEngine(
            channels={"late": ch},
            channel_configs={"late": cfg},
        )

        result_slot: list[FanoutResult] = []

        def _run() -> None:
            result_slot.append(engine.fanout(_notice("n-late")))

        fanout_thread = threading.Thread(target=_run, daemon=True)
        fanout_thread.start()

        assert ch.wait_until_started(timeout=5.0), "第一次投递应已启动"

        time.sleep(0.1)
        ch.release()

        fanout_thread.join(timeout=3.0)
        assert not fanout_thread.is_alive(), "fanout 应已结束"

        assert len(result_slot) == 1
        result = result_slot[0]
        r = result.channel_results["late"]

        assert r.status == ChannelDeliveryStatus.SUCCESS, (
            f"后台线程释放后应最终成功，实际状态={r.status}, error={r.final_error}"
        )
        assert ch.delivered_count == 1, "实际投递应只发生一次"
        assert any(a.success for a in r.attempts_detail), (
            f"attempts_detail 中必须至少包含一条成功记录，实际: "
            f"{[(a.attempt_number, a.success) for a in r.attempts_detail]}"
        )
        assert len(r.attempts_detail) >= 2, (
            f"至少应有一次超时尝试 + 一次捕获后台成功的尝试，实际尝试次数={len(r.attempts_detail)}"
        )
        assert r.attempts == len(r.attempts_detail)
        assert r.attempts_detail[-1].success is True, "最后一条尝试记录应为成功"


class TestNoTimeoutTOCTOU:
    def test_thread_finishes_within_timeout_boundary_never_wrongly_marked_timeout(self):
        class NearBoundaryChannel(NotificationChannel):
            def __init__(self, name: str, work_time: float) -> None:
                self._name = name
                self._work_time = work_time
                self._delivered: list[Notification] = []

            @property
            def name(self) -> str:
                return self._name

            @property
            def delivered_count(self) -> int:
                return len(self._delivered)

            def deliver(self, notification: Notification) -> None:
                deadline = time.monotonic() + self._work_time
                while time.monotonic() < deadline:
                    pass
                self._delivered.append(notification)

        timeout = 0.02
        for delta in (-0.005, -0.002, 0.0, 0.002, 0.005):
            work_time = timeout + delta
            ch = NearBoundaryChannel("boundary", work_time)
            cfg = ChannelConfig(channel_name="boundary", timeout=timeout, max_attempts=1)
            engine = FanoutEngine(
                channels={"boundary": ch},
                channel_configs={"boundary": cfg},
            )
            for _ in range(10):
                ch._delivered.clear()
                result = engine.fanout(_notice("n-boundary"))
                r = result.channel_results["boundary"]
                if ch.delivered_count == 1:
                    assert r.status == ChannelDeliveryStatus.SUCCESS, (
                        f"work_time={work_time:.3f}s，timeout={timeout}s，"
                        f"投递实际成功但被误判为 {r.status}"
                    )
                    assert r.final_error is None
                else:
                    assert r.status in (
                        ChannelDeliveryStatus.TIMEOUT,
                        ChannelDeliveryStatus.SUCCESS,
                    )

    def test_failed_exception_after_timeout_still_returns_failed_not_timeout(self):
        ch = InMemoryChannel("fail-fast")
        ch.set_fail_next_n(1)
        cfg = ChannelConfig(channel_name="fail-fast", timeout=5.0, max_attempts=1)
        engine = FanoutEngine(
            channels={"fail-fast": ch},
            channel_configs={"fail-fast": cfg},
        )
        result = engine.fanout(_notice())
        r = result.channel_results["fail-fast"]
        assert r.status == ChannelDeliveryStatus.FAILED
        assert r.status != ChannelDeliveryStatus.TIMEOUT
        assert isinstance(r.final_error, RuntimeError)
        assert ch.delivered_count == 0

