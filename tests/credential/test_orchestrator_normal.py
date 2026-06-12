from __future__ import annotations

import pytest

from solocoder_py.credential import (
    CredentialRotator,
    CredentialVersion,
    ManualClock,
    MemoryWriteTarget,
    RotationConfig,
    RotationPhase,
    TrafficStats,
)


class TestCreateRotation:
    def test_create_rotation_success(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
    ):
        state = rotator.create_rotation(sample_config)
        assert state.name == "db-password"
        assert state.phase == RotationPhase.IDLE
        assert state.current_traffic_percentage == 0
        assert state.config.old_credential == "old-secret-123"
        assert state.config.new_credential == "new-secret-456"

    def test_create_duplicate_rotation_raises(
        self,
        rotator_with_rotation: CredentialRotator,
        sample_config: RotationConfig,
    ):
        from solocoder_py.credential import RotationAlreadyExistsError

        with pytest.raises(RotationAlreadyExistsError):
            rotator_with_rotation.create_rotation(sample_config)

    def test_list_rotations(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        sample_config_small_steps: RotationConfig,
    ):
        rotator.create_rotation(sample_config)
        rotator.create_rotation(sample_config_small_steps)
        rotations = rotator.list_rotations()
        assert len(rotations) == 2
        names = {r.name for r in rotations}
        assert names == {"db-password", "api-key"}


class TestDualWritePhase:
    def test_start_dual_write(
        self,
        rotator_with_rotation: CredentialRotator,
        manual_clock: ManualClock,
    ):
        state = rotator_with_rotation.start_dual_write("db-password")
        assert state.phase == RotationPhase.DUAL_WRITE
        assert state.dual_write_started_at == manual_clock.now()
        assert state.current_traffic_percentage == 0

    def test_dual_write_writes_both_sides(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(10)

        result = rotator_with_rotation.perform_write("db-password", {"key": "value"})
        assert result.old_success is True
        assert result.new_success is True
        assert result.any_failed is False
        assert result.all_succeeded is True

        old_writes = write_target.get_old_writes()
        new_writes = write_target.get_new_writes()
        assert len(old_writes) == 1
        assert len(new_writes) == 1
        assert old_writes[0] == ("old-secret-123", {"key": "value"})
        assert new_writes[0] == ("new-secret-456", {"key": "value"})

    def test_dual_write_read_uses_old_credential(
        self,
        rotator_with_rotation: CredentialRotator,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(50)

        for i in range(100):
            cred, version = rotator_with_rotation.route_read(
                "db-password", f"req-{i}"
            )
            assert cred == "old-secret-123"
            assert version == CredentialVersion.OLD

    def test_check_dual_write_complete_before_elapsed(
        self,
        rotator_with_rotation: CredentialRotator,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(100)
        assert rotator_with_rotation.check_dual_write_complete("db-password") is False

    def test_check_dual_write_complete_after_elapsed(
        self,
        rotator_with_rotation: CredentialRotator,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        manual_clock.advance(400)
        assert rotator_with_rotation.check_dual_write_complete("db-password") is True

    def test_dual_write_multiple_writes(
        self,
        rotator_with_rotation: CredentialRotator,
        write_target: MemoryWriteTarget,
        manual_clock: ManualClock,
    ):
        rotator_with_rotation.start_dual_write("db-password")
        for i in range(5):
            rotator_with_rotation.perform_write(
                "db-password", {"index": i, "data": f"payload-{i}"}
            )

        old_writes = write_target.get_old_writes()
        new_writes = write_target.get_new_writes()
        assert len(old_writes) == 5
        assert len(new_writes) == 5
        for i in range(5):
            assert old_writes[i][1]["index"] == i
            assert new_writes[i][1]["index"] == i


class TestCanaryTrafficAdvancement:
    def _start_canary(
        self,
        rotator: CredentialRotator,
        manual_clock: ManualClock,
        config: RotationConfig,
    ) -> None:
        rotator.create_rotation(config)
        rotator.start_dual_write(config.credential_name)
        manual_clock.advance(config.dual_write_duration_seconds + 10)
        rotator.start_canary(config.credential_name)

    def test_start_canary_sets_initial_step(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._start_canary(rotator, manual_clock, sample_config)
        state = rotator.get_state("db-password")
        assert state.phase == RotationPhase.CANARY
        assert state.current_traffic_percentage == 20
        assert state.canary_started_at == manual_clock.now()

    def test_advance_traffic_by_step(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._start_canary(rotator, manual_clock, sample_config)
        expected = [20, 40, 60, 80, 100]
        for pct in expected:
            state = rotator.get_state("db-password")
            assert state.current_traffic_percentage == pct
            if pct < 100:
                rotator.advance_traffic("db-password")

    def test_advance_final_step_completes_rotation(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._start_canary(rotator, manual_clock, sample_config)
        for _ in range(3):
            rotator.advance_traffic("db-password")
        state = rotator.advance_traffic("db-password")
        assert state.phase == RotationPhase.COMPLETED
        assert state.current_traffic_percentage == 100
        assert state.completed_at == manual_clock.now()

    def test_manual_complete_rotation(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        state = rotator.complete_rotation("db-password")
        assert state.phase == RotationPhase.COMPLETED
        assert state.current_traffic_percentage == 100


class TestCanaryTrafficRouting:
    def _setup_canary_at(
        self,
        rotator: CredentialRotator,
        manual_clock: ManualClock,
        sample_config: RotationConfig,
        target_pct: int,
    ) -> None:
        rotator.create_rotation(sample_config)
        rotator.start_dual_write("db-password")
        manual_clock.advance(500)
        rotator.start_canary("db-password")
        while True:
            state = rotator.get_state("db-password")
            if state.current_traffic_percentage >= target_pct:
                break
            rotator.advance_traffic("db-password")

    def test_canary_routes_some_to_new(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._setup_canary_at(rotator, manual_clock, sample_config, 50)
        old_count = 0
        new_count = 0
        for i in range(10000):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            if version == CredentialVersion.OLD:
                old_count += 1
                assert cred == "old-secret-123"
            else:
                new_count += 1
                assert cred == "new-secret-456"
        assert old_count + new_count == 10000
        assert 4000 <= new_count <= 6000

    def test_completed_routes_all_new(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._setup_canary_at(rotator, manual_clock, sample_config, 100)
        for i in range(1000):
            cred, version = rotator.route_read("db-password", f"req-{i}")
            assert cred == "new-secret-456"
            assert version == CredentialVersion.NEW

    def test_canary_dual_write_continues(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
        write_target: MemoryWriteTarget,
    ):
        self._setup_canary_at(rotator, manual_clock, sample_config, 40)
        rotator.perform_write("db-password", {"test": "canary-write"})
        old_writes = write_target.get_old_writes()
        new_writes = write_target.get_new_writes()
        assert len(old_writes) == 1
        assert len(new_writes) == 1

    def test_set_traffic_percentage_directly(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._setup_canary_at(rotator, manual_clock, sample_config, 20)
        state = rotator.set_traffic_percentage("db-password", 33)
        assert state.current_traffic_percentage == 33
        assert state.phase == RotationPhase.CANARY

    def test_set_100_percent_completes(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._setup_canary_at(rotator, manual_clock, sample_config, 20)
        state = rotator.set_traffic_percentage("db-password", 100)
        assert state.phase == RotationPhase.COMPLETED
        assert state.current_traffic_percentage == 100


class TestCanaryHealthEvaluation:
    def _setup_canary(
        self,
        rotator: CredentialRotator,
        manual_clock: ManualClock,
        sample_config_small_steps: RotationConfig,
    ) -> None:
        rotator.create_rotation(sample_config_small_steps)
        rotator.start_dual_write("api-key")
        manual_clock.advance(100)
        rotator.start_canary("api-key")

    def test_healthy_canary_passes_evaluation(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._setup_canary(rotator, manual_clock, sample_config_small_steps)

        for i in range(100):
            _, version = rotator.route_read("api-key", f"req-{i}")
            rotator.record_request_result("api-key", version, is_error=False)

        healthy, record = rotator.evaluate_canary_health("api-key")
        assert healthy is True
        assert record is None

    def test_evaluate_records_traffic_stats(
        self,
        rotator: CredentialRotator,
        sample_config_small_steps: RotationConfig,
        manual_clock: ManualClock,
    ):
        self._setup_canary(rotator, manual_clock, sample_config_small_steps)

        for i in range(50):
            _, version = rotator.route_read("api-key", f"req-{i}")
            rotator.record_request_result("api-key", version, is_error=False)

        rotator.evaluate_canary_health("api-key")
        state = rotator.get_state("api-key")
        assert state.traffic_stats.total_requests == 50


class TestFullIntegrationWorkflow:
    def test_complete_rotation_lifecycle(
        self,
        rotator: CredentialRotator,
        sample_config: RotationConfig,
        manual_clock: ManualClock,
        write_target: MemoryWriteTarget,
    ):
        config = sample_config
        rotator.create_rotation(config)

        state = rotator.get_state("db-password")
        assert state.phase == RotationPhase.IDLE

        rotator.start_dual_write("db-password")
        state = rotator.get_state("db-password")
        assert state.phase == RotationPhase.DUAL_WRITE

        for i in range(5):
            result = rotator.perform_write(
                "db-password", {"batch": 1, "seq": i}
            )
            assert result.all_succeeded is True

        assert len(write_target.get_old_writes()) == 5
        assert len(write_target.get_new_writes()) == 5

        manual_clock.advance(config.dual_write_duration_seconds + 50)
        assert rotator.check_dual_write_complete("db-password") is True

        rotator.start_canary("db-password")
        state = rotator.get_state("db-password")
        assert state.phase == RotationPhase.CANARY
        assert state.current_traffic_percentage == config.traffic_step_percentage

        for pct in [40, 60, 80]:
            for i in range(30):
                _, version = rotator.route_read("db-password", f"canary-{pct}-{i}")
                rotator.record_request_result(
                    "db-password", version, is_error=False
                )

            healthy, record = rotator.evaluate_canary_health("db-password")
            assert healthy is True
            assert record is None

            rotator.advance_traffic("db-password")

        for i in range(30):
            _, version = rotator.route_read("db-password", f"canary-final-{i}")
            rotator.record_request_result(
                "db-password", version, is_error=False
            )
        healthy, record = rotator.evaluate_canary_health("db-password")
        assert healthy is True
        assert record is None
        state = rotator.advance_traffic("db-password")
        assert state.phase == RotationPhase.COMPLETED

        state = rotator.get_state("db-password")
        assert state.phase == RotationPhase.COMPLETED
        assert state.current_traffic_percentage == 100
        assert state.completed_at is not None
        assert state.max_traffic_reached == 100

        for i in range(100):
            cred, version = rotator.route_read("db-password", f"final-{i}")
            assert cred == config.new_credential
            assert version == CredentialVersion.NEW

        result = rotator.perform_write("db-password", {"final": True})
        assert result.new_success is True
        assert result.old_success is False

        fallback_history = rotator.get_fallback_history("db-password")
        assert len(fallback_history) == 0
