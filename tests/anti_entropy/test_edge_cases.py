from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.anti_entropy import AntiEntropyEngine, Replica, SyncError


class TestBoundaryConditions:
    def test_both_replicas_empty(self, engine):
        diff = engine.diff()
        assert not diff.has_differences
        assert diff.diff_count == 0

        result = engine.sync_bidirectional()
        assert result.total_synced == 0
        assert not result.has_conflicts
        assert engine.is_consistent()

    def test_one_replica_empty_full_sync(self, replica_a, replica_b, engine):
        for i in range(100):
            replica_a.put(f"key_{i}", f"value_{i}", version=i + 1)

        result = engine.sync_a_to_b()

        assert result.a_to_b_count == 100
        assert len(replica_b) == 100
        for i in range(100):
            assert replica_b.get(f"key_{i}").value == f"value_{i}"
            assert replica_b.get(f"key_{i}").version == i + 1
        assert engine.is_consistent()

    def test_all_entries_conflict(self, replica_a, replica_b, engine):
        for i in range(10):
            replica_a.put(f"key_{i}", f"a_val_{i}", version=2)
            replica_b.put(f"key_{i}", f"b_val_{i}", version=2)

        diff = engine.diff()
        assert len(diff.conflicts) == 10
        assert diff.has_conflicts

        result = engine.sync_bidirectional()
        assert result.has_conflicts
        assert len(result.conflict_keys) == 10
        assert result.total_synced == 0

        assert not engine.is_consistent()

    def test_zero_version_entries(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value_a", version=0)
        replica_b.put("key1", "value_b", version=0)

        diff = engine.diff()
        assert "key1" in diff.conflicts
        assert diff.conflicts["key1"].entry_a.version == 0

    def test_single_entry_sync(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=1)

        result = engine.sync_a_to_b()
        assert result.a_to_b_count == 1
        assert result.total_synced == 1
        assert len(result.synced_keys) == 1
        assert "key1" in result.synced_keys
        assert engine.is_consistent()

    def test_large_number_of_entries(self, replica_a, replica_b, engine):
        for i in range(1000):
            replica_a.put(f"k_{i}", f"v_a_{i}", version=i % 5 + 1)
            replica_b.put(f"k_{i}", f"v_b_{i}", version=i % 3 + 1)

        diff = engine.diff()
        assert diff.diff_count > 0

        result = engine.sync_bidirectional()
        assert result.total_synced > 0
        assert not engine.is_consistent()


class TestIdempotency:
    def test_repeated_sync_same_result(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=3)
        replica_a.put("key2", "value2", version=2)
        replica_b.put("key1", "old", version=1)

        for _ in range(5):
            result = engine.sync_a_to_b()

        assert replica_b.get("key1").value == "value1"
        assert replica_b.get("key1").version == 3
        assert replica_b.get("key2").value == "value2"
        assert engine.is_consistent()

    def test_repeated_bidirectional_sync(self, replica_a, replica_b, engine):
        replica_a.put("a_key", "a_val", version=1)
        replica_a.put("shared", "a_ver", version=3)
        replica_b.put("b_key", "b_val", version=2)
        replica_b.put("shared", "b_ver", version=1)

        for _ in range(10):
            result = engine.sync_bidirectional()

        assert engine.is_consistent()
        assert replica_a.get("a_key").value == "a_val"
        assert replica_a.get("b_key").value == "b_val"
        assert replica_a.get("shared").value == "a_ver"
        assert replica_a.get("shared").version == 3

    def test_sync_after_no_changes(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=1)
        replica_a.put("key2", "value2", version=2)
        engine.sync_a_to_b()
        assert engine.is_consistent()

        result = engine.sync_a_to_b()
        assert result.total_synced == 0
        assert len(result.synced_keys) == 0

        result2 = engine.sync_bidirectional()
        assert result2.total_synced == 0


class TestConcurrencyAndConsistency:
    def test_concurrent_reads_during_sync(self, replica_a, replica_b, engine):
        for i in range(100):
            replica_a.put(f"key_{i}", f"value_{i}", version=1)

        results = []

        def read_replica_b():
            for _ in range(50):
                keys = replica_b.keys()
                results.append(len(keys))
                time.sleep(0.001)

        reader = threading.Thread(target=read_replica_b)
        reader.start()

        engine.sync_a_to_b()

        reader.join()
        assert engine.is_consistent()
        assert len(replica_b) == 100

    def test_concurrent_writes_during_sync(self, replica_a, replica_b, engine):
        for i in range(50):
            replica_a.put(f"key_{i}", f"value_{i}", version=1)

        def add_more_keys():
            time.sleep(0.001)
            for i in range(50, 100):
                replica_a.put(f"key_{i}", f"value_{i}", version=1)

        writer = threading.Thread(target=add_more_keys)
        writer.start()

        engine.sync_a_to_b()

        writer.join()

        engine.sync_a_to_b()
        assert len(replica_b) == 100

    def test_thread_safe_put(self, replica_a):
        def put_keys(prefix, count):
            for i in range(count):
                replica_a.put(f"{prefix}_{i}", f"val_{i}", version=1)

        threads = []
        for t in range(5):
            thread = threading.Thread(target=put_keys, args=(f"t{t}", 20))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(replica_a) == 100


class TestEngineValidation:
    def test_engine_requires_both_replicas(self):
        r = Replica(replica_id="a")
        with pytest.raises(SyncError, match="Both replicas must be provided"):
            AntiEntropyEngine(replica_a=r, replica_b=None)
        with pytest.raises(SyncError, match="Both replicas must be provided"):
            AntiEntropyEngine(replica_a=None, replica_b=r)

    def test_engine_rejects_same_replica_id(self):
        r1 = Replica(replica_id="same")
        r2 = Replica(replica_id="same")
        with pytest.raises(SyncError, match="Replica IDs must be different"):
            AntiEntropyEngine(replica_a=r1, replica_b=r2)


class TestDiffResultProperties:
    def test_has_differences_empty(self, engine):
        diff = engine.diff()
        assert not diff.has_differences

    def test_has_differences_with_only_a(self, replica_a, engine):
        replica_a.put("key1", "value1", version=1)
        diff = engine.diff()
        assert diff.has_differences

    def test_has_conflicts_no_conflicts(self, engine):
        diff = engine.diff()
        assert not diff.has_conflicts

    def test_has_conflicts_with_conflict(self, replica_a, replica_b, engine):
        replica_a.put("key1", "val_a", version=1)
        replica_b.put("key1", "val_b", version=1)
        diff = engine.diff()
        assert diff.has_conflicts

    def test_diff_count(self, replica_a, replica_b, engine):
        replica_a.put("only_a", "val", version=1)
        replica_b.put("only_b", "val", version=1)
        replica_a.put("mismatch", "a_val", version=2)
        replica_b.put("mismatch", "b_val", version=1)
        replica_a.put("conflict", "a_val", version=1)
        replica_b.put("conflict", "b_val", version=1)
        replica_a.put("identical", "same", version=1)
        replica_b.put("identical", "same", version=1)

        diff = engine.diff()
        assert diff.diff_count == 4


class TestSyncResultProperties:
    def test_total_synced(self, replica_a, replica_b, engine):
        replica_a.put("a1", "v1", version=1)
        replica_a.put("a2", "v2", version=1)
        replica_b.put("b1", "v3", version=1)

        result = engine.sync_bidirectional()
        assert result.total_synced == 3
        assert result.a_to_b_count == 2
        assert result.b_to_a_count == 1

    def test_has_conflicts_false(self, engine):
        result = engine.sync_bidirectional()
        assert not result.has_conflicts

    def test_has_conflicts_true(self, replica_a, replica_b, engine):
        replica_a.put("key", "a_val", version=1)
        replica_b.put("key", "b_val", version=1)
        result = engine.sync_bidirectional()
        assert result.has_conflicts
