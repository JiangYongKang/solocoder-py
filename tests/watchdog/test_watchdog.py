from __future__ import annotations

import pytest

from solocoder_py.watchdog import (
    EntityAlreadyRegisteredError,
    EntityConfig,
    EntityNotFoundError,
    EntityStatus,
    HeartbeatWatchdog,
    InvalidConfigError,
    ManualClock,
    WatchdogConfig,
)

from .conftest import make_config, make_watchdog


class TestWatchdogConfig:
    def test_default_config_is_valid(self):
        cfg = WatchdogConfig()
        assert cfg.default_lease_ttl == 10.0
        assert cfg.default_debounce_count == 3

    def test_invalid_lease_ttl_raises(self):
        with pytest.raises(InvalidConfigError):
            WatchdogConfig(default_lease_ttl=0)
        with pytest.raises(InvalidConfigError):
            WatchdogConfig(default_lease_ttl=-1)

    def test_invalid_debounce_count_raises(self):
        with pytest.raises(InvalidConfigError):
            WatchdogConfig(default_debounce_count=0)
        with pytest.raises(InvalidConfigError):
            WatchdogConfig(default_debounce_count=-1)


class TestEntityConfig:
    def test_valid_entity_config(self):
        cfg = EntityConfig(
            entity_id="e1",
            lease_ttl=5.0,
            debounce_count=2,
        )
        assert cfg.entity_id == "e1"
        assert cfg.lease_ttl == 5.0
        assert cfg.debounce_count == 2

    def test_empty_entity_id_raises(self):
        with pytest.raises(InvalidConfigError):
            EntityConfig(entity_id="", lease_ttl=5.0, debounce_count=2)

    def test_invalid_lease_ttl_raises(self):
        with pytest.raises(InvalidConfigError):
            EntityConfig(entity_id="e1", lease_ttl=0, debounce_count=2)
        with pytest.raises(InvalidConfigError):
            EntityConfig(entity_id="e1", lease_ttl=-1, debounce_count=2)

    def test_invalid_debounce_count_raises(self):
        with pytest.raises(InvalidConfigError):
            EntityConfig(entity_id="e1", lease_ttl=5.0, debounce_count=0)
        with pytest.raises(InvalidConfigError):
            EntityConfig(entity_id="e1", lease_ttl=5.0, debounce_count=-1)


class TestManualClock:
    def test_initial_time(self):
        clock = ManualClock(start_time=100.0)
        assert clock.now() == 100.0

    def test_advance(self):
        clock = ManualClock()
        clock.advance(5.0)
        assert clock.now() == 5.0
        clock.advance(3.0)
        assert clock.now() == 8.0

    def test_advance_negative_raises(self):
        clock = ManualClock()
        with pytest.raises(ValueError):
            clock.advance(-1)

    def test_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0


class TestWatchdogRegistration:
    def test_register_entity(self, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1")
        assert watchdog.is_registered("e1") is True
        entity = watchdog.get_entity("e1")
        assert entity is not None
        assert entity.entity_id == "e1"
        assert entity.status == EntityStatus.ACTIVE

    def test_register_entity_with_custom_params(self, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=5.0, debounce_count=2)
        entity = watchdog.get_entity("e1")
        assert entity.lease_ttl == 5.0
        assert entity.debounce_count == 2

    def test_register_duplicate_entity_raises(self, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1")
        with pytest.raises(EntityAlreadyRegisteredError):
            watchdog.register_entity("e1")

    def test_register_from_config(self, watchdog: HeartbeatWatchdog):
        cfg = EntityConfig(entity_id="e1", lease_ttl=7.0, debounce_count=4)
        watchdog.register_entity_from_config(cfg)
        entity = watchdog.get_entity("e1")
        assert entity.lease_ttl == 7.0
        assert entity.debounce_count == 4

    def test_unregister_entity(self, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1")
        watchdog.unregister_entity("e1")
        assert watchdog.is_registered("e1") is False
        assert watchdog.get_entity("e1") is None

    def test_unregister_nonexistent_raises(self, watchdog: HeartbeatWatchdog):
        with pytest.raises(EntityNotFoundError):
            watchdog.unregister_entity("nonexistent")

    def test_get_nonexistent_entity_returns_none(self, watchdog: HeartbeatWatchdog):
        assert watchdog.get_entity("nonexistent") is None


class TestWatchdogHeartbeat:
    def test_heartbeat_updates_last_heartbeat_time(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1")
        clock.advance(5.0)
        watchdog.heartbeat("e1")
        entity = watchdog.get_entity("e1")
        assert entity.last_heartbeat_at == 5.0

    def test_heartbeat_unregistered_entity_raises(self, watchdog: HeartbeatWatchdog):
        with pytest.raises(EntityNotFoundError):
            watchdog.heartbeat("nonexistent")

    def test_heartbeat_resets_inactive_streak(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=3)
        clock.advance(3.0)
        watchdog.check_expired()
        watchdog.check_expired()
        entity = watchdog.get_entity("e1")
        assert entity.inactive_streak == 2
        watchdog.heartbeat("e1")
        entity = watchdog.get_entity("e1")
        assert entity.inactive_streak == 0


class TestLeaseExpiration:
    def test_entity_not_expired_before_ttl(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=10.0)
        clock.advance(9.9)
        expired = watchdog.check_expired()
        assert expired == []
        entity = watchdog.get_entity("e1")
        assert entity.status == EntityStatus.ACTIVE

    def test_heartbeat_at_exact_expiry_boundary(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=10.0, debounce_count=3)
        clock.advance(10.0)
        expired = watchdog.check_expired()
        assert "e1" in expired or len(expired) == 0
        entity_before = watchdog.get_entity("e1")
        streak_before = entity_before.inactive_streak
        watchdog.heartbeat("e1")
        entity_after = watchdog.get_entity("e1")
        assert entity_after.status == EntityStatus.ACTIVE
        assert entity_after.inactive_streak == 0
        assert entity_after.last_heartbeat_at == 10.0

    def test_entity_expires_after_ttl_plus_debounce(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=5.0, debounce_count=3)
        clock.advance(6.0)
        for i in range(2):
            expired = watchdog.check_expired()
            assert expired == []
            entity = watchdog.get_entity("e1")
            assert entity.status == EntityStatus.ACTIVE
            assert entity.inactive_streak == i + 1
        expired = watchdog.check_expired()
        assert "e1" in expired
        entity = watchdog.get_entity("e1")
        assert entity.status == EntityStatus.INACTIVE

    def test_different_entities_different_ttl(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=5.0, debounce_count=1)
        watchdog.register_entity("e2", lease_ttl=15.0, debounce_count=1)
        clock.advance(10.0)
        expired = watchdog.check_expired()
        assert "e1" in expired
        assert "e2" not in expired
        entity1 = watchdog.get_entity("e1")
        entity2 = watchdog.get_entity("e2")
        assert entity1.status == EntityStatus.INACTIVE
        assert entity2.status == EntityStatus.ACTIVE

    def test_debounce_at_boundary(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=5)
        clock.advance(3.0)
        for i in range(4):
            expired = watchdog.check_expired()
            assert expired == []
            entity = watchdog.get_entity("e1")
            assert entity.status == EntityStatus.ACTIVE
            assert entity.inactive_streak == i + 1
        expired = watchdog.check_expired()
        assert "e1" in expired
        entity = watchdog.get_entity("e1")
        assert entity.status == EntityStatus.INACTIVE
        assert entity.inactive_streak == 5

    def test_expired_check_only_affects_active_entities(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=1.0, debounce_count=1)
        clock.advance(2.0)
        watchdog.check_expired()
        assert watchdog.get_entity("e1").status == EntityStatus.INACTIVE
        clock.advance(100.0)
        expired = watchdog.check_expired()
        assert expired == []


class TestDebounceRecovery:
    def test_recovery_during_debounce_window(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=5)
        clock.advance(3.0)
        watchdog.check_expired()
        watchdog.check_expired()
        entity = watchdog.get_entity("e1")
        assert entity.inactive_streak == 2
        assert entity.status == EntityStatus.ACTIVE
        watchdog.heartbeat("e1")
        entity = watchdog.get_entity("e1")
        assert entity.inactive_streak == 0
        assert entity.status == EntityStatus.ACTIVE
        clock.advance(3.0)
        watchdog.check_expired()
        watchdog.check_expired()
        entity = watchdog.get_entity("e1")
        assert entity.status == EntityStatus.ACTIVE
        assert entity.inactive_streak == 2

    def test_recovery_at_last_debounce_boundary(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=3)
        clock.advance(3.0)
        watchdog.check_expired()
        watchdog.check_expired()
        entity = watchdog.get_entity("e1")
        assert entity.inactive_streak == 2
        assert entity.status == EntityStatus.ACTIVE
        watchdog.heartbeat("e1")
        entity = watchdog.get_entity("e1")
        assert entity.inactive_streak == 0
        assert entity.status == EntityStatus.ACTIVE

    def test_inactive_entity_recovery_on_heartbeat(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=2)
        clock.advance(3.0)
        watchdog.check_expired()
        watchdog.check_expired()
        entity = watchdog.get_entity("e1")
        assert entity.status == EntityStatus.INACTIVE
        watchdog.heartbeat("e1")
        entity = watchdog.get_entity("e1")
        assert entity.status == EntityStatus.ACTIVE
        assert entity.inactive_streak == 0


class TestInactiveCallback:
    def test_callback_triggered_on_final_inactive(self, clock: ManualClock):
        triggered = []

        def on_inactive(entity_id: str) -> None:
            triggered.append(entity_id)

        watchdog = make_watchdog(clock=clock)
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=3, on_inactive=on_inactive)
        clock.advance(3.0)
        watchdog.check_expired()
        assert triggered == []
        watchdog.check_expired()
        assert triggered == []
        watchdog.check_expired()
        assert triggered == ["e1"]

    def test_callback_not_triggered_during_debounce(self, clock: ManualClock):
        triggered = []

        def on_inactive(entity_id: str) -> None:
            triggered.append(entity_id)

        watchdog = make_watchdog(clock=clock)
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=5, on_inactive=on_inactive)
        clock.advance(3.0)
        for _ in range(4):
            watchdog.check_expired()
        assert triggered == []

    def test_callback_not_triggered_on_recovery(self, clock: ManualClock):
        triggered = []

        def on_inactive(entity_id: str) -> None:
            triggered.append(entity_id)

        watchdog = make_watchdog(clock=clock)
        watchdog.register_entity("e1", lease_ttl=2.0, debounce_count=3, on_inactive=on_inactive)
        clock.advance(3.0)
        watchdog.check_expired()
        watchdog.check_expired()
        watchdog.heartbeat("e1")
        clock.advance(3.0)
        watchdog.check_expired()
        watchdog.check_expired()
        assert triggered == []

    def test_callback_exception_is_suppressed(self, clock: ManualClock):
        def bad_callback(entity_id: str) -> None:
            raise RuntimeError("boom")

        watchdog = make_watchdog(clock=clock)
        watchdog.register_entity("e1", lease_ttl=1.0, debounce_count=1, on_inactive=bad_callback)
        clock.advance(2.0)
        expired = watchdog.check_expired()
        assert "e1" in expired

    def test_multiple_entities_callbacks(self, clock: ManualClock):
        triggered = []

        def on_inactive(entity_id: str) -> None:
            triggered.append(entity_id)

        watchdog = make_watchdog(clock=clock)
        watchdog.register_entity("e1", lease_ttl=1.0, debounce_count=1, on_inactive=on_inactive)
        watchdog.register_entity("e2", lease_ttl=2.0, debounce_count=1, on_inactive=on_inactive)
        watchdog.register_entity("e3", lease_ttl=1.0, debounce_count=1)
        clock.advance(3.0)
        expired = watchdog.check_expired()
        assert set(expired) == {"e1", "e2", "e3"}
        assert "e1" in triggered
        assert "e2" in triggered
        assert len(triggered) == 2


class TestWatchdogQueries:
    def test_get_all_entities(self, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1")
        watchdog.register_entity("e2")
        all_entities = watchdog.get_all_entities()
        assert set(all_entities.keys()) == {"e1", "e2"}

    def test_get_active_and_inactive(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=1.0, debounce_count=1)
        watchdog.register_entity("e2", lease_ttl=100.0, debounce_count=1)
        clock.advance(5.0)
        watchdog.check_expired()
        active = watchdog.get_active_entities()
        inactive = watchdog.get_inactive_entities()
        assert "e1" in inactive
        assert "e1" not in active
        assert "e2" in active
        assert "e2" not in inactive

    def test_check_all(self, clock: ManualClock, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1", lease_ttl=1.0, debounce_count=1)
        watchdog.register_entity("e2", lease_ttl=100.0, debounce_count=1)
        clock.advance(5.0)
        statuses = watchdog.check_all()
        assert statuses["e1"] == EntityStatus.INACTIVE
        assert statuses["e2"] == EntityStatus.ACTIVE

    def test_get_entity_returns_clone(self, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1")
        entity = watchdog.get_entity("e1")
        entity.status = EntityStatus.INACTIVE
        stored = watchdog.get_entity("e1")
        assert stored.status == EntityStatus.ACTIVE

    def test_get_all_entities_returns_clones(self, watchdog: HeartbeatWatchdog):
        watchdog.register_entity("e1")
        all_entities = watchdog.get_all_entities()
        all_entities["e1"].status = EntityStatus.INACTIVE
        stored = watchdog.get_entity("e1")
        assert stored.status == EntityStatus.ACTIVE


class TestNormalFlowScenarios:
    def test_single_entity_full_lifecycle(self, clock: ManualClock):
        triggered = []

        def on_inactive(entity_id: str) -> None:
            triggered.append(entity_id)

        watchdog = make_watchdog(clock=clock)
        watchdog.register_entity("svc-1", lease_ttl=5.0, debounce_count=3, on_inactive=on_inactive)
        assert watchdog.get_entity("svc-1").status == EntityStatus.ACTIVE
        for i in range(10):
            clock.advance(3.0)
            watchdog.heartbeat("svc-1")
        entity = watchdog.get_entity("svc-1")
        assert entity.status == EntityStatus.ACTIVE
        assert entity.inactive_streak == 0
        clock.advance(6.0)
        watchdog.check_expired()
        watchdog.check_expired()
        assert watchdog.get_entity("svc-1").status == EntityStatus.ACTIVE
        assert triggered == []
        watchdog.check_expired()
        assert watchdog.get_entity("svc-1").status == EntityStatus.INACTIVE
        assert triggered == ["svc-1"]
        clock.advance(1.0)
        watchdog.heartbeat("svc-1")
        assert watchdog.get_entity("svc-1").status == EntityStatus.ACTIVE

    def test_multiple_entities_mixed_behavior(self, clock: ManualClock):
        watchdog = make_watchdog(clock=clock)
        watchdog.register_entity("e1", lease_ttl=3.0, debounce_count=2)
        watchdog.register_entity("e2", lease_ttl=20.0, debounce_count=2)
        watchdog.register_entity("e3", lease_ttl=5.0, debounce_count=1)
        clock.advance(6.0)
        watchdog.heartbeat("e2")
        watchdog.check_expired()
        watchdog.check_expired()
        statuses = watchdog.check_all()
        assert statuses["e1"] == EntityStatus.INACTIVE
        assert statuses["e2"] == EntityStatus.ACTIVE
        assert statuses["e3"] == EntityStatus.INACTIVE
