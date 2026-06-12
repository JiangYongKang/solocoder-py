import threading

import pytest

from solocoder_py.apikey import APIKeyNotFoundError, APIKeyManager

from .conftest import FakeClock, make_manager


class TestUsageTrackingBasics:
    def test_check_permission_does_not_increment_usage(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:x", "write:x"])

        for _ in range(5):
            manager.check_permission(result.key_secret, "read:x")
        manager.require_permission(result.key_secret, "write:x")

        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == 0
        assert stats.last_used_at is None

    def test_verify_key_increments_usage(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])

        for _ in range(3):
            manager.verify_key(result.key_secret)

        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == 3

    def test_mixed_calls_only_verify_counts(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read", "write"])

        manager.verify_key(result.key_secret)
        manager.check_permission(result.key_secret, "read")
        manager.require_permission(result.key_secret, "write")
        manager.verify_key(result.key_secret)
        manager.check_permission(result.key_secret, "read")

        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == 2

    def test_verify_key_increments_total_uses(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])

        for i in range(5):
            manager.verify_key(result.key_secret)

        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == 5

    def test_verify_key_updates_last_used_at(self):
        clock = FakeClock(start_time=1000000.0)
        manager = make_manager(clock=clock)
        result = manager.create_key("user-1", ["read"])

        manager.verify_key(result.key_secret)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.last_used_at == 1000000.0

        clock.advance(60.0)
        manager.verify_key(result.key_secret)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.last_used_at == 1000060.0

    def test_get_usage_stats_not_found(self):
        manager = make_manager()
        with pytest.raises(APIKeyNotFoundError):
            manager.get_usage_stats("nonexistent")

    def test_get_usage_stats_empty_id_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="key_id cannot be empty"):
            manager.get_usage_stats("")

    def test_window_count_within_window(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, window_seconds=3600)
        result = manager.create_key("user-1", ["read"])

        for i in range(10):
            clock.advance(60.0)
            manager.verify_key(result.key_secret)

        stats = manager.get_usage_stats(result.key_id)
        assert stats.window_uses == 10

    def test_window_count_expired_entries_removed(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, window_seconds=300)
        result = manager.create_key("user-1", ["read"])

        manager.verify_key(result.key_secret)
        clock.advance(200.0)
        manager.verify_key(result.key_secret)
        clock.advance(200.0)
        manager.verify_key(result.key_secret)

        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == 3
        assert stats.window_uses == 2

    def test_window_count_all_expired(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, window_seconds=300)
        result = manager.create_key("user-1", ["read"])

        for _ in range(5):
            manager.verify_key(result.key_secret)

        clock.advance(600.0)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == 5
        assert stats.window_uses == 0

    def test_window_count_zero_after_long_idle(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, window_seconds=3600)
        result = manager.create_key("user-1", ["read"])

        for _ in range(100):
            manager.verify_key(result.key_secret)

        clock.advance(7200.0)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == 100
        assert stats.window_uses == 0


class TestUsageSorting:
    def test_list_keys_by_usage_descending(self):
        clock = FakeClock(start_time=1000000.0)
        manager = make_manager(clock=clock)

        result1 = manager.create_key("user-1", ["read"])
        result2 = manager.create_key("user-1", ["write"])
        result3 = manager.create_key("user-1", ["admin"])

        for _ in range(10):
            manager.verify_key(result1.key_secret)
        for _ in range(5):
            manager.verify_key(result2.key_secret)
        for _ in range(20):
            manager.verify_key(result3.key_secret)

        keys = manager.list_keys_by_usage(subject="user-1", descending=True)
        assert len(keys) == 3
        assert keys[0].key_id == result3.key_id
        assert keys[1].key_id == result1.key_id
        assert keys[2].key_id == result2.key_id

    def test_list_keys_by_usage_ascending(self):
        clock = FakeClock(start_time=1000000.0)
        manager = make_manager(clock=clock)

        result1 = manager.create_key("user-1", ["read"])
        result2 = manager.create_key("user-1", ["write"])
        result3 = manager.create_key("user-1", ["admin"])

        for _ in range(10):
            manager.verify_key(result1.key_secret)
        for _ in range(5):
            manager.verify_key(result2.key_secret)
        for _ in range(20):
            manager.verify_key(result3.key_secret)

        keys = manager.list_keys_by_usage(subject="user-1", descending=False)
        assert len(keys) == 3
        assert keys[0].key_id == result2.key_id
        assert keys[1].key_id == result1.key_id
        assert keys[2].key_id == result3.key_id

    def test_list_keys_by_usage_limit(self):
        manager = make_manager()

        for i in range(10):
            manager.create_key(f"user-{i}", ["read"])

        keys = manager.list_keys_by_usage(limit=5)
        assert len(keys) == 5

    def test_list_keys_by_usage_all_subjects(self):
        manager = make_manager()
        manager.create_key("user-1", ["read"])
        manager.create_key("user-2", ["write"])

        keys = manager.list_keys_by_usage()
        assert len(keys) == 2


class TestIdleDetection:
    def test_key_not_idle_after_creation(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, idle_threshold_days=30)
        result = manager.create_key("user-1", ["read"])

        stats = manager.get_usage_stats(result.key_id)
        assert stats.is_idle is False
        assert stats.idle_days == 0.0

    def test_key_becomes_idle_after_threshold(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, idle_threshold_days=30)
        result = manager.create_key("user-1", ["read"])

        manager.verify_key(result.key_secret)

        clock.advance(30 * 86400.0)

        stats = manager.get_usage_stats(result.key_id)
        assert stats.is_idle is True
        assert stats.idle_days >= 30.0

    def test_key_not_idle_before_threshold(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, idle_threshold_days=30)
        result = manager.create_key("user-1", ["read"])

        manager.verify_key(result.key_secret)
        clock.advance(20 * 86400.0)

        stats = manager.get_usage_stats(result.key_id)
        assert stats.is_idle is False

    def test_list_idle_keys(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, idle_threshold_days=30)

        result1 = manager.create_key("user-1", ["read"])
        result2 = manager.create_key("user-1", ["write"])

        manager.verify_key(result1.key_secret)
        manager.verify_key(result2.key_secret)

        clock.advance(20 * 86400.0)
        manager.verify_key(result1.key_secret)

        clock.advance(20 * 86400.0)

        idle_keys = manager.list_idle_keys(subject="user-1")
        idle_ids = {k.key_id for k in idle_keys}
        assert result2.key_id in idle_ids
        assert result1.key_id not in idle_ids

    def test_list_idle_keys_custom_threshold(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, idle_threshold_days=30)
        result = manager.create_key("user-1", ["read"])

        manager.verify_key(result.key_secret)
        clock.advance(10 * 86400.0)

        idle_keys = manager.list_idle_keys(idle_days=5)
        assert len(idle_keys) == 1
        assert idle_keys[0].key_id == result.key_id

    def test_list_idle_keys_empty_when_none_idle(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        manager.verify_key(result.key_secret)

        idle_keys = manager.list_idle_keys()
        assert idle_keys == []

    def test_list_idle_keys_revoked_keys_excluded(self):
        clock = FakeClock(start_time=1000000.0)
        manager = APIKeyManager(clock=clock, idle_threshold_days=1)
        result = manager.create_key("user-1", ["read"])

        manager.revoke_key(result.key_id)
        clock.advance(2 * 86400.0)

        idle_keys = manager.list_idle_keys()
        assert result.key_id not in {k.key_id for k in idle_keys}


class TestSubjectUsageStats:
    def test_get_subject_usage_stats(self):
        manager = make_manager()
        result1 = manager.create_key("user-1", ["read"])
        result2 = manager.create_key("user-1", ["write"])

        manager.verify_key(result1.key_secret)
        manager.verify_key(result1.key_secret)
        manager.verify_key(result2.key_secret)

        stats_list = manager.get_subject_usage_stats("user-1")
        assert len(stats_list) == 2

        total_uses = sum(s.total_uses for _, s in stats_list)
        assert total_uses == 3

    def test_get_subject_usage_stats_empty_subject(self):
        manager = make_manager()
        stats = manager.get_subject_usage_stats("nobody")
        assert stats == []

    def test_get_subject_usage_stats_empty_subject_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="subject cannot be empty"):
            manager.get_subject_usage_stats("")


class TestConcurrentUsage:
    def test_concurrent_verify_count_accuracy(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])

        num_threads = 20
        calls_per_thread = 50

        def worker():
            for _ in range(calls_per_thread):
                manager.verify_key(result.key_secret)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = manager.get_usage_stats(result.key_id)
        assert stats.total_uses == num_threads * calls_per_thread

    def test_concurrent_create_keys_uniqueness(self):
        manager = make_manager()
        created_keys = []

        num_threads = 10
        keys_per_thread = 20

        def worker(thread_id):
            for i in range(keys_per_thread):
                r = manager.create_key(f"user-{thread_id}-{i}", ["read"])
                created_keys.append(r)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ids = [k.key_id for k in created_keys]
        secrets = [k.key_secret for k in created_keys]
        assert len(set(ids)) == num_threads * keys_per_thread
        assert len(set(secrets)) == num_threads * keys_per_thread
