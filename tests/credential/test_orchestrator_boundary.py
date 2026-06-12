from __future__ import annotations

import pytest

from solocoder_py.credential import (
    CredentialRotator,
    CredentialVersion,
    FallbackReason,
    InvalidTrafficPercentageError,
    ManualClock,
    MemoryWriteTarget,
    RotationConfig,
    RotationPhase,
    TrafficStats,
)


class TestZeroPercentTrafficBoundary:
    def _setup_dual_write_phase(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ) -> None:
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(10)

    def test_dual_write_zero_percent_all_old(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._setup_dual_write_phase(rotator, sample_config, manual_clock)
        for i in range(1000):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            assert cred == "old-secret-123"
            assert version == CredentialVersion.OLD

    def test_rolled_back_zero_percent_all_old(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")
        rotator.advance_traffic("db-password")
        rotator.manual_rollback("db-password")

        for i in range(500):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            assert cred == "old-secret-123"
            assert version == CredentialVersion.OLD

    def test_cooldown_phase_all_old(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        rotator.create_rotation(config)
        rotator.start_dual_write("api-key")
        manual_clock.advance(100)
        rotator.start_canary("api-key")

        for i in range(config.consecutive_failure_threshold):
            rotator.record_request_result(
                "api-key", CredentialVersion.NEW, is_error=True
            )

        for i in range(1000):
            cred, version = rotator.route_read("api-key", f"req-{i}")
            assert cred == config.old_credential
            assert version == CredentialVersion.OLD


class TestHundredPercentTrafficBoundary:
    def test_completed_phase_all_new(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")
        for _ in range(3):
            rotator.advance_traffic("db-password")
        rotator.advance_traffic("db-password")

        for i in range(1000):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            assert cred == "new-secret-456"
            assert version == CredentialVersion.NEW

    def test_set_100_percent_before_step(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")

        state = rotator.set_traffic_percentage("db-password", 100)
        assert state.phase == RotationPhase.COMPLETED

        for i in range(500):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            assert cred == "new-secret-456"
            assert version == CredentialVersion.NEW


class TestDualWriteFailureIsolation:
    def test_old_write_failure_does_not_affect_new(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(10)

        write_target.set_old_should_fail(True)
        result = rotator_with_rotation.perform_write(
            "db-password", {"data": "test1"}
        )

        assert result.old_success is False
        assert result.new_success is True
        assert result.any_failed is True
        assert result.all_succeeded is False
        assert result.old_error is not None
        assert result.new_error is None

        assert len(write_target.get_new_writes()) == 1
        assert write_target.get_new_writes()[0] == (
            "new-secret-456",
            {"data": "test1"},
        )

        failures = rotator_with_rotation.get_write_failure_history("db-password")
        assert len(failures) == 1
        assert failures[0].side.value == "OLD"
        assert "old system write failure" in failures[0].error_message

    def test_new_write_failure_does_not_affect_old(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(10)

        write_target.set_new_should_fail(True)
        result = rotator_with_rotation.perform_write(
            "db-password", {"data": "test2"}
        )

        assert result.old_success is True
        assert result.new_success is False
        assert result.old_error is None
        assert result.new_error is not None

        assert len(write_target.get_old_writes()) == 1
        assert write_target.get_old_writes()[0] == (
            "old-secret-123",
            {"data": "test2"},
        )

        failures = rotator_with_rotation.get_write_failure_history("db-password")
        assert len(failures) == 1
        assert failures[0].side.value == "NEW"

    def test_old_write_recovery_after_failure(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(10)

        write_target.set_old_should_fail(True)
        result1 = rotator_with_rotation.perform_write("db-password", {"n": 1})
        assert result1.old_success is False
        assert result1.new_success is True

        write_target.set_old_should_fail(False)
        result2 = rotator_with_rotation.perform_write("db-password", {"n": 2})
        assert result2.old_success is True
        assert result2.new_success is True
        assert result2.all_succeeded is True

        assert len(write_target.get_old_writes()) == 1
        assert len(write_target.get_new_writes()) == 2

    def test_alternating_side_failures_recorded_separately(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(10)

        write_target.fail_old_next_n(1)
        result1 = rotator_with_rotation.perform_write("db-password", {"n": 1})
        assert result1.old_success is False
        assert result1.new_success is True

        write_target.fail_new_next_n(1)
        result2 = rotator_with_rotation.perform_write("db-password", {"n": 2})
        assert result2.old_success is True
        assert result2.new_success is False

        result3 = rotator_with_rotation.perform_write("db-password", {"n": 3})
        assert result3.all_succeeded is True

        failures = rotator_with_rotation.get_write_failure_history("db-password")
        assert len(failures) == 2
        assert failures[0].side.value == "OLD"
        assert failures[1].side.value == "NEW"

    def test_canary_phase_dual_write_continues_after_old_failure(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
        write_target: MemoryWriteTarget,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")

        write_target.fail_old_next_n(1)
        result = rotator.perform_write("db-password", {"k": "v"})

        assert result.old_success is False
        assert result.new_success is True
        assert len(write_target.get_new_writes()) == 1


class TestErrorRateThresholdBoundary:
    def _setup_canary(
        self,
        rotator: CredentialRotator,
        config: RotationConfig,
        manual_clock: ManualClock,
    ) -> None:
        rotator.create_rotation(config)
        rotator.start_dual_write(config.credential_name)
        manual_clock.advance(config.dual_write_duration_seconds + 10)
        rotator.start_canary(config.credential_name)

    def test_error_rate_at_threshold_not_triggered(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = RotationConfig(
            credential_name="threshold-not-trigger",
            old_credential="old",
            new_credential="new",
            dual_write_duration_seconds=60.0,
            traffic_step_percentage=100,
            max_error_rate=0.10,
            consecutive_failure_threshold=999,
            cooldown_seconds=60.0,
            min_requests_for_evaluation=100,
        )
        self._setup_canary(rotator, config, manual_clock)

        total_requests = 200
        expected_errors = int(total_requests * config.max_error_rate)

        for i in range(total_requests):
            _, version = rotator.route_read(config.credential_name, f"req-{i}")
            is_error = i < expected_errors
            rotator.record_request_result(
                config.credential_name, version, is_error=is_error
            )

        stats = rotator.get_stats(config.credential_name)
        error_rate = stats.new_error_rate

        healthy, record = rotator.evaluate_canary_health(config.credential_name)
        if error_rate <= config.max_error_rate:
            assert healthy is True
            assert record is None
        else:
            assert healthy is False
            assert record is not None

    def test_error_rate_exactly_at_threshold_boundary(
        self,
        rotator: CredentialRotator,
        manual_clock: ManualClock,
    ):
        config = RotationConfig(
            credential_name="threshold-test",
            old_credential="old",
            new_credential="new",
            dual_write_duration_seconds=60.0,
            traffic_step_percentage=100,
            max_error_rate=0.10,
            consecutive_failure_threshold=999,
            cooldown_seconds=60.0,
            min_requests_for_evaluation=100,
        )
        self._setup_canary(rotator, config, manual_clock)

        for i in range(100):
            rotator.route_read("threshold-test", f"req-{i}")
            is_error = i < 10
            rotator.record_request_result(
                "threshold-test", CredentialVersion.NEW, is_error=is_error
            )

        stats = rotator.get_stats("threshold-test")
        assert stats.new_error_rate == pytest.approx(0.10)

        healthy, record = rotator.evaluate_canary_health("threshold-test")
        assert healthy is True
        assert record is None

    def test_error_rate_just_above_threshold(
        self,
        rotator: CredentialRotator,
        manual_clock: ManualClock,
    ):
        config = RotationConfig(
            credential_name="just-above",
            old_credential="old",
            new_credential="new",
            dual_write_duration_seconds=60.0,
            traffic_step_percentage=100,
            max_error_rate=0.10,
            consecutive_failure_threshold=999,
            cooldown_seconds=60.0,
            min_requests_for_evaluation=100,
        )
        self._setup_canary(rotator, config, manual_clock)

        for i in range(100):
            rotator.route_read("just-above", f"req-{i}")
            is_error = i < 11
            rotator.record_request_result(
                "just-above", CredentialVersion.NEW, is_error=is_error
            )

        stats = rotator.get_stats("just-above")
        assert stats.new_error_rate == pytest.approx(0.11)

        healthy, record = rotator.evaluate_canary_health("just-above")
        assert healthy is False
        assert record is not None
        assert record.reason == FallbackReason.ERROR_RATE_EXCEEDED
        assert record.traffic_percentage_at_fallback == 100

        state = rotator.get_state("just-above")
        assert state.phase == RotationPhase.COOLDOWN

    def test_below_min_requests_skips_error_rate_evaluation(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = RotationConfig(
            credential_name="min-req-skip",
            old_credential="old",
            new_credential="new",
            dual_write_duration_seconds=60.0,
            traffic_step_percentage=50,
            max_error_rate=0.10,
            consecutive_failure_threshold=999,
            cooldown_seconds=60.0,
            min_requests_for_evaluation=100,
        )
        self._setup_canary(rotator, config, manual_clock)
        rotator.set_traffic_percentage(config.credential_name, 50)

        min_req = config.min_requests_for_evaluation
        for i in range(min_req - 1):
            _, version = rotator.route_read(config.credential_name, f"req-{i}")
            rotator.record_request_result(
                config.credential_name, version, is_error=True
            )

        stats = rotator.get_stats(config.credential_name)
        assert stats.new_error_rate == 1.0

        healthy, record = rotator.evaluate_canary_health(config.credential_name)
        assert healthy is True
        assert record is None
        state = rotator.get_state(config.credential_name)
        assert state.phase == RotationPhase.CANARY


class TestTrafficPercentageBoundaries:
    def test_set_traffic_zero_percent(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")
        rotator.advance_traffic("db-password")

        state = rotator.set_traffic_percentage("db-password", 0)
        assert state.current_traffic_percentage == 0
        assert state.phase == RotationPhase.CANARY

        for i in range(100):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            assert cred == "old-secret-123"
            assert version == CredentialVersion.OLD

    def test_invalid_negative_percentage_raises(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")

        with pytest.raises(InvalidTrafficPercentageError):
            rotator.set_traffic_percentage("db-password", -1)

    def test_invalid_over_100_percentage_raises(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")

        with pytest.raises(InvalidTrafficPercentageError):
            rotator.set_traffic_percentage("db-password", 101)
