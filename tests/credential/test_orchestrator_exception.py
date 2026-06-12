from __future__ import annotations

import pytest

from solocoder_py.credential import (
    CredentialRotator,
    CredentialVersion,
    FallbackReason,
    InvalidRotationPhaseError,
    ManualClock,
    MemoryWriteTarget,
    RotationConfig,
    RotationPhase,
    RotationStore,
    TrafficRouter,
)


class TestConsecutiveFailuresAutoFallback:
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

    def test_consecutive_failures_triggers_fallback_via_record(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_canary(rotator, config, manual_clock)
        rotator.advance_traffic(config.credential_name)

        state_before = rotator.get_state(config.credential_name)
        traffic_before = state_before.current_traffic_percentage

        last_record = None
        for i in range(config.consecutive_failure_threshold):
            last_record = rotator.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )

        assert last_record is not None
        assert last_record.reason == FallbackReason.CONSECUTIVE_FAILURES
        assert last_record.failure_count == config.consecutive_failure_threshold
        assert last_record.traffic_percentage_at_fallback == traffic_before

        state_after = rotator.get_state(config.credential_name)
        assert state_after.phase == RotationPhase.COOLDOWN
        assert state_after.current_traffic_percentage == 0
        assert state_after.cooldown_started_at == manual_clock.now()
        assert len(state_after.fallback_records) == 1

    def test_consecutive_failures_triggers_fallback_via_evaluate(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = RotationConfig(
            credential_name="eval-test",
            old_credential="old",
            new_credential="new",
            dual_write_duration_seconds=60.0,
            traffic_step_percentage=50,
            max_error_rate=0.10,
            consecutive_failure_threshold=999,
            cooldown_seconds=60.0,
            min_requests_for_evaluation=20,
        )
        self._setup_canary(rotator, config, manual_clock)
        rotator.set_traffic_percentage(config.credential_name, 50)
        rotator.reset_stats(config.credential_name)

        total = 50
        new_successes = 0
        new_failures = 0
        i = 0
        while new_successes + new_failures < total:
            _, version = rotator.route_read(config.credential_name, f"req-{i}")
            i += 1
            if version == CredentialVersion.NEW:
                is_error = (new_failures) < 15
                rotator.record_request_result(
                    config.credential_name, version, is_error=is_error
                )
                if is_error:
                    new_failures += 1
                else:
                    new_successes += 1
            else:
                rotator.record_request_result(
                    config.credential_name, version, is_error=False
                )

        state_mid = rotator.get_state(config.credential_name)
        if state_mid.phase == RotationPhase.CANARY:
            healthy, record = rotator.evaluate_canary_health(config.credential_name)
            assert healthy is False
            assert record is not None
            assert record.reason == FallbackReason.ERROR_RATE_EXCEEDED

            state = rotator.get_state(config.credential_name)
            assert state.phase == RotationPhase.COOLDOWN
        else:
            assert state_mid.phase == RotationPhase.COOLDOWN
            assert len(state_mid.fallback_records) >= 1

    def test_fallback_recorded_correctly(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_canary(rotator, config, manual_clock)
        rotator.advance_traffic(config.credential_name)
        rotator.advance_traffic(config.credential_name)

        traffic_pct = rotator.get_state(config.credential_name).current_traffic_percentage
        for _ in range(config.consecutive_failure_threshold):
            record = rotator.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )

        assert record is not None
        assert record.timestamp == manual_clock.now()
        assert record.traffic_percentage_at_fallback == traffic_pct
        assert record.failure_count == config.consecutive_failure_threshold
        assert "Consecutive failures" in record.detail

        history = rotator.get_fallback_history(config.credential_name)
        assert len(history) == 1
        assert history[0] is record

    def test_success_resets_consecutive_counter(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_canary(rotator, config, manual_clock)

        threshold = config.consecutive_failure_threshold
        for i in range(threshold - 1):
            record = rotator.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )
            assert record is None

        rotator.record_request_result(
            config.credential_name, CredentialVersion.NEW, is_error=False
        )

        for i in range(threshold - 1):
            record = rotator.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )
            assert record is None

        state = rotator.get_state(config.credential_name)
        assert state.phase == RotationPhase.CANARY

    def test_fallback_routes_all_to_old(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_canary(rotator, config, manual_clock)
        rotator.advance_traffic(config.credential_name)

        for _ in range(config.consecutive_failure_threshold):
            rotator.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )

        for i in range(500):
            cred, version = rotator.route_read(config.credential_name, f"req-{i}")
            assert cred == config.old_credential
            assert version == CredentialVersion.OLD


class TestCooldownPeriod:
    def _setup_cooldown(
        self,
        rotator: CredentialRotator,
        config: RotationConfig,
        manual_clock: ManualClock,
    ) -> None:
        rotator.create_rotation(config)
        rotator.start_dual_write(config.credential_name)
        manual_clock.advance(config.dual_write_duration_seconds + 10)
        rotator.start_canary(config.credential_name)
        rotator.advance_traffic(config.credential_name)
        for _ in range(config.consecutive_failure_threshold):
            rotator.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )

    def test_cooldown_phase_blocks_advance(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_cooldown(rotator, config, manual_clock)

        with pytest.raises(InvalidRotationPhaseError):
            rotator.advance_traffic(config.credential_name)

    def test_cooldown_blocks_start_canary_before_elapsed(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_cooldown(rotator, config, manual_clock)

        manual_clock.advance(config.cooldown_seconds - 10)
        assert rotator.check_cooldown_complete(config.credential_name) is False

        with pytest.raises(InvalidRotationPhaseError):
            rotator.start_canary(config.credential_name)

    def test_cooldown_complete_allows_reentry(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_cooldown(rotator, config, manual_clock)

        manual_clock.advance(config.cooldown_seconds + 10)
        assert rotator.check_cooldown_complete(config.credential_name) is True

        state = rotator.start_canary(config.credential_name)
        assert state.phase == RotationPhase.CANARY
        assert state.current_traffic_percentage > 0

    def test_set_traffic_percentage_in_cooldown_switches_to_canary(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_cooldown(rotator, config, manual_clock)
        manual_clock.advance(config.cooldown_seconds + 10)

        state = rotator.set_traffic_percentage(config.credential_name, 15)
        assert state.phase == RotationPhase.CANARY
        assert state.current_traffic_percentage == 15

    def test_set_zero_traffic_stays_in_canary(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_cooldown(rotator, config, manual_clock)
        manual_clock.advance(config.cooldown_seconds + 10)
        rotator.start_canary(config.credential_name)

        state = rotator.set_traffic_percentage(config.credential_name, 0)
        assert state.phase == RotationPhase.CANARY
        assert state.current_traffic_percentage == 0


class TestDualWriteAllFailures:
    def test_both_sides_fail_recorded_separately(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(10)

        write_target.set_old_should_fail(True)
        write_target.set_new_should_fail(True)

        result = rotator_with_rotation.perform_write(
            "db-password", {"critical": "data"}
        )

        assert result.old_success is False
        assert result.new_success is False
        assert result.all_succeeded is False
        assert result.any_failed is True
        assert result.old_error is not None
        assert result.new_error is not None

        failures = rotator_with_rotation.get_write_failure_history("db-password")
        assert len(failures) == 2

        sides = {f.side.value for f in failures}
        assert sides == {"OLD", "NEW"}

    def test_write_failure_history_preserved(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(10)

        write_target.fail_old_next_n(2)
        write_target.fail_new_next_n(1)

        for i in range(3):
            rotator_with_rotation.perform_write("db-password", {"n": i})

        failures = rotator_with_rotation.get_write_failure_history("db-password")
        assert len(failures) >= 2

        old_failures = [f for f in failures if f.side.value == "OLD"]
        new_failures = [f for f in failures if f.side.value == "NEW"]
        assert len(old_failures) == 2
        assert len(new_failures) == 1

    def test_canary_phase_both_writes_fail(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")

        write_target.set_old_should_fail(True)
        write_target.set_new_should_fail(True)

        result = rotator.perform_write("db-password", {"x": 1})
        assert result.old_success is False
        assert result.new_success is False

        state = rotator.get_state("db-password")
        assert state.phase == RotationPhase.CANARY


class TestManualTrafficRollback:
    def _setup_canary_at(
        self,
        rotator: CredentialRotator,
        config: RotationConfig,
        manual_clock: ManualClock,
        target: int,
    ) -> None:
        rotator.create_rotation(config)
        rotator.start_dual_write(config.credential_name)
        manual_clock.advance(config.dual_write_duration_seconds + 10)
        rotator.start_canary(config.credential_name)
        while True:
            state = rotator.get_state(config.credential_name)
            if state.current_traffic_percentage >= target:
                break
            rotator.advance_traffic(config.credential_name)

    def test_manual_rollback_to_lower_percentage(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config
        self._setup_canary_at(rotator, config, manual_clock, 60)

        state = rotator.set_traffic_percentage(config.credential_name, 20)
        assert state.current_traffic_percentage == 20
        assert state.phase == RotationPhase.CANARY

        new_count = 0
        for i in range(10000):
            _, version = rotator.route_read(config.credential_name, f"req-{i}")
            if version == CredentialVersion.NEW:
                new_count += 1
        assert 1500 <= new_count <= 2500

    def test_manual_rollback_to_zero(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_canary_at(rotator, config, manual_clock, 50)

        state = rotator.set_traffic_percentage(config.credential_name, 0)
        assert state.current_traffic_percentage == 0
        assert state.phase == RotationPhase.CANARY

        for i in range(500):
            cred, version = rotator.route_read(config.credential_name, f"req-{i}")
            assert cred == config.old_credential
            assert version == CredentialVersion.OLD

    def test_manual_rollback_preserves_max_traffic(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config
        self._setup_canary_at(rotator, config, manual_clock, 80)

        state_before = rotator.get_state(config.credential_name)
        max_before = state_before.max_traffic_reached

        rotator.set_traffic_percentage(config.credential_name, 10)

        state_after = rotator.get_state(config.credential_name)
        assert state_after.max_traffic_reached == max_before
        assert state_after.max_traffic_reached == 80

    def test_advance_after_manual_rollback(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_canary_at(rotator, config, manual_clock, 50)

        rotator.set_traffic_percentage(config.credential_name, 20)
        state = rotator.advance_traffic(config.credential_name)
        assert state.current_traffic_percentage == 20 + config.traffic_step_percentage


class TestAutoRecoveryAfterCooldown:
    def _setup_with_cooldown(
        self,
        rotator: CredentialRotator,
        config: RotationConfig,
        manual_clock: ManualClock,
    ) -> int:
        rotator.create_rotation(config)
        rotator.start_dual_write(config.credential_name)
        manual_clock.advance(config.dual_write_duration_seconds + 10)
        rotator.start_canary(config.credential_name)
        traffic_before = rotator.get_state(config.credential_name).current_traffic_percentage
        for _ in range(config.consecutive_failure_threshold):
            rotator.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )
        return traffic_before

    def test_auto_recover_after_cooldown(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_with_cooldown(rotator, config, manual_clock)

        state_before = rotator.get_state(config.credential_name)
        assert state_before.phase == RotationPhase.COOLDOWN

        manual_clock.advance(config.cooldown_seconds + 10)
        recovered = rotator.try_auto_recover(config.credential_name)

        assert recovered is True
        state_after = rotator.get_state(config.credential_name)
        assert state_after.phase == RotationPhase.CANARY
        assert state_after.current_traffic_percentage > 0
        assert state_after.cooldown_started_at is None

        stats = rotator.get_stats(config.credential_name)
        assert stats.total_requests == 0

    def test_auto_recover_before_cooldown_complete_fails(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        self._setup_with_cooldown(rotator, config, manual_clock)

        manual_clock.advance(config.cooldown_seconds // 2)
        recovered = rotator.try_auto_recover(config.credential_name)
        assert recovered is False

        state = rotator.get_state(config.credential_name)
        assert state.phase == RotationPhase.COOLDOWN

    def test_auto_recover_disabled_config(
        self,
        rotator: CredentialRotator,
        manual_clock: ManualClock,
    ):
        config = RotationConfig(
            credential_name="no-auto",
            old_credential="old",
            new_credential="new",
            dual_write_duration_seconds=60.0,
            traffic_step_percentage=10,
            max_error_rate=0.10,
            consecutive_failure_threshold=3,
            cooldown_seconds=60.0,
            min_requests_for_evaluation=10,
            auto_recover_enabled=False,
        )
        self._setup_with_cooldown(rotator, config, manual_clock)

        manual_clock.advance(config.cooldown_seconds + 100)
        recovered = rotator.try_auto_recover(config.credential_name)
        assert recovered is False

        state = rotator.get_state(config.credential_name)
        assert state.phase == RotationPhase.COOLDOWN

    def test_auto_recover_not_in_cooldown_phase(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        config = sample_config_small_steps
        rotator.create_rotation(config)
        rotator.start_dual_write(config.credential_name)
        manual_clock.advance(config.dual_write_duration_seconds + 10)
        rotator.start_canary(config.credential_name)

        recovered = rotator.try_auto_recover(config.credential_name)
        assert recovered is False


class TestCrashRecovery:
    def test_snapshot_and_restore_state(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(100)
        rotator.perform_write("db-password", {"k": "v"})

        snapshot = rotator.snapshot()
        assert "db-password" in snapshot

        clock2 = ManualClock(_current_time=manual_clock.now() + 50)
        store2 = RotationStore()
        router2 = TrafficRouter()
        write_target2 = MemoryWriteTarget()
        rotator2 = CredentialRotator(
            write_target=write_target2,
            clock=clock2,
            store=store2,
            router=router2,
        )
        rotator2.restore(snapshot)

        restored = rotator2.get_state("db-password")
        assert restored.phase == RotationPhase.DUAL_WRITE
        assert restored.dual_write_started_at is not None
        assert len(restored.write_failure_records) == 0
        assert restored.config.old_credential == "old-secret-123"

        result = rotator2.perform_write("db-password", {"k2": "v2"})
        assert result.all_succeeded is True
        assert len(write_target2.get_old_writes()) == 1

    def test_restore_canary_state_with_traffic(
        self,
        manual_clock: ManualClock,
        sample_config_small_steps: RotationConfig,
    ):
        store1 = RotationStore()
        router1 = TrafficRouter()
        write_target1 = MemoryWriteTarget()
        rotator1 = CredentialRotator(
            write_target=write_target1,
            clock=manual_clock,
            store=store1,
            router=router1,
        )

        config = sample_config_small_steps
        rotator1.create_rotation(config)
        rotator1.start_dual_write(config.credential_name)
        manual_clock.advance(config.dual_write_duration_seconds + 10)
        rotator1.start_canary(config.credential_name)
        rotator1.advance_traffic(config.credential_name)
        rotator1.advance_traffic(config.credential_name)

        for i in range(25):
            _, version = rotator1.route_read(config.credential_name, f"req-{i}")
            rotator1.record_request_result(config.credential_name, version, is_error=False)

        traffic_before = rotator1.get_state(config.credential_name).current_traffic_percentage
        snapshot = rotator1.snapshot()

        clock2 = ManualClock(_current_time=manual_clock.now() + 30)
        store2 = RotationStore()
        router2 = TrafficRouter()
        write_target2 = MemoryWriteTarget()
        rotator2 = CredentialRotator(
            write_target=write_target2,
            clock=clock2,
            store=store2,
            router=router2,
        )
        rotator2.restore(snapshot)

        restored = rotator2.get_state(config.credential_name)
        assert restored.phase == RotationPhase.CANARY
        assert restored.current_traffic_percentage == traffic_before
        assert restored.traffic_stats.total_requests >= 20

        result = rotator2.advance_traffic(config.credential_name)
        assert result.current_traffic_percentage == traffic_before + config.traffic_step_percentage

    def test_restore_cooldown_state_with_fallback(
        self,
        manual_clock: ManualClock,
        sample_config_small_steps: RotationConfig,
    ):
        store1 = RotationStore()
        router1 = TrafficRouter()
        write_target1 = MemoryWriteTarget()
        rotator1 = CredentialRotator(
            write_target=write_target1,
            clock=manual_clock,
            store=store1,
            router=router1,
        )

        config = sample_config_small_steps
        rotator1.create_rotation(config)
        rotator1.start_dual_write(config.credential_name)
        manual_clock.advance(100)
        rotator1.start_canary(config.credential_name)
        for _ in range(config.consecutive_failure_threshold):
            rotator1.record_request_result(
                config.credential_name, CredentialVersion.NEW, is_error=True
            )

        fallbacks_before = len(rotator1.get_fallback_history(config.credential_name))
        snapshot = rotator1.snapshot()

        clock2 = ManualClock(_current_time=manual_clock.now() + 10)
        store2 = RotationStore()
        router2 = TrafficRouter()
        write_target2 = MemoryWriteTarget()
        rotator2 = CredentialRotator(
            write_target=write_target2,
            clock=clock2,
            store=store2,
            router=router2,
        )
        rotator2.restore(snapshot)

        restored = rotator2.get_state(config.credential_name)
        assert restored.phase == RotationPhase.COOLDOWN
        assert len(restored.fallback_records) == fallbacks_before
        assert restored.cooldown_started_at is not None

        for i in range(200):
            cred, version = rotator2.route_read(config.credential_name, f"req-{i}")
            assert cred == config.old_credential
            assert version == CredentialVersion.OLD

    def test_serialize_and_deserialize_individual(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")

        json_str = rotator.serialize_state("db-password")
        assert isinstance(json_str, str)
        assert "db-password" in json_str

        restored = rotator.restore_from_serialized(json_str)
        assert restored.name == "db-password"
        assert restored.phase == RotationPhase.CANARY


class TestInvalidPhaseOperations:
    def test_start_dual_write_from_non_idle_raises(
        self,
        rotator_with_rotation: CredentialRotator,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator_with_rotation.start_canary("db-password")

        with pytest.raises(InvalidRotationPhaseError):
            rotator_with_rotation.start_dual_write("db-password")

    def test_start_canary_before_dual_write_complete(
        self,
        rotator_with_rotation: CredentialRotator,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(50)

        with pytest.raises(InvalidRotationPhaseError, match="not yet elapsed"):
            rotator_with_rotation.start_canary("db-password")

    def test_route_read_in_idle_raises(
        self,
        rotator_with_rotation: CredentialRotator,
    ):
        with pytest.raises(InvalidRotationPhaseError):
            rotator_with_rotation.route_read("db-password", "req-1")

    def test_evaluate_health_non_canary_raises(
        self,
        rotator_with_rotation: CredentialRotator,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")

        with pytest.raises(InvalidRotationPhaseError):
            rotator_with_rotation.evaluate_canary_health("db-password")

    def test_manual_rollback_completed_raises(
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

        with pytest.raises(InvalidRotationPhaseError):
            rotator.manual_rollback("db-password")

    def test_nonexistent_rotation_raises(
        self,
        rotator: CredentialRotator,
    ):
        from solocoder_py.credential import RotationNotFoundError

        with pytest.raises(RotationNotFoundError):
            rotator.get_state("nonexistent")

        with pytest.raises(RotationNotFoundError):
            rotator.start_dual_write("nonexistent")


class TestManualRollback:
    def test_manual_rollback_records_properly(
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
        rotator.advance_traffic("db-password")

        state_before = rotator.get_state("db-password")
        traffic_before = state_before.current_traffic_percentage

        state = rotator.manual_rollback("db-password", reason="业务方反馈问题")
        assert state.phase == RotationPhase.ROLLED_BACK
        assert state.current_traffic_percentage == 0
        assert state.rolled_back_at == manual_clock.now()
        assert len(state.fallback_records) == 1

        record = state.fallback_records[0]
        assert record.reason == FallbackReason.MANUAL
        assert record.traffic_percentage_at_fallback == traffic_before
        assert record.detail == "业务方反馈问题"

        for i in range(200):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            assert cred == sample_config.old_credential
            assert version == CredentialVersion.OLD

    def test_rolled_back_continues_dual_write(
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
        rotator.manual_rollback("db-password")

        result = rotator.perform_write("db-password", {"after": "rollback"})
        assert result.old_success is True
        assert result.new_success is True
        assert len(write_target.get_old_writes()) == 1
        assert len(write_target.get_new_writes()) == 1
