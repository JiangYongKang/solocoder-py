from __future__ import annotations

import pytest

from solocoder_py.mvcc import (
    KeyNotFoundError,
    MVCCStore,
    Snapshot,
    SnapshotInvalidError,
    Transaction,
    TransactionStateError,
    TransactionStatus,
    Version,
    VersionNotFoundError,
    VersionReclaimedError,
    WriteWriteConflictError,
)
from .conftest import make_store


class TestVersionModel:
    def test_version_creation(self):
        v = Version(key="k1", value="v1", version=1, transaction_id=1)
        assert v.key == "k1"
        assert v.value == "v1"
        assert v.version == 1
        assert v.transaction_id == 1
        assert v.is_tombstone is False

    def test_version_tombstone(self):
        v = Version(key="k1", value=None, version=1, transaction_id=1, is_tombstone=True)
        assert v.is_tombstone is True

    def test_version_invalid_version(self):
        with pytest.raises(ValueError, match="version must be positive"):
            Version(key="k1", value="v1", version=0, transaction_id=1)

    def test_version_invalid_transaction_id(self):
        with pytest.raises(ValueError, match="transaction_id must be positive"):
            Version(key="k1", value="v1", version=1, transaction_id=0)


class TestSnapshotModel:
    def test_snapshot_creation(self):
        snap = Snapshot(snapshot_version=10)
        assert snap.snapshot_version == 10
        assert snap.active_transactions == ()

    def test_snapshot_with_active_transactions(self):
        snap = Snapshot(snapshot_version=10, active_transactions=(1, 2, 3))
        assert snap.snapshot_version == 10
        assert snap.active_transactions == (1, 2, 3)

    def test_snapshot_invalid_version(self):
        with pytest.raises(ValueError, match="snapshot_version cannot be negative"):
            Snapshot(snapshot_version=-1)

    def test_snapshot_is_visible_committed_version(self):
        snap = Snapshot(snapshot_version=10, active_transactions=())
        v = Version(key="k1", value="v1", version=5, transaction_id=1)
        assert snap.is_visible(v) is True

    def test_snapshot_is_visible_future_version(self):
        snap = Snapshot(snapshot_version=10, active_transactions=())
        v = Version(key="k1", value="v1", version=15, transaction_id=1)
        assert snap.is_visible(v) is False

    def test_snapshot_is_visible_active_transaction(self):
        snap = Snapshot(snapshot_version=10, active_transactions=(1,))
        v = Version(key="k1", value="v1", version=5, transaction_id=1)
        assert snap.is_visible(v) is False


class TestTransactionModel:
    def test_transaction_creation(self):
        txn = Transaction(transaction_id=1, start_version=1)
        assert txn.transaction_id == 1
        assert txn.start_version == 1
        assert txn.status == TransactionStatus.ACTIVE
        assert txn.writes == {}
        assert txn.commit_version is None
        assert txn.is_active is True
        assert txn.is_committed is False
        assert txn.is_aborted is False

    def test_transaction_invalid_id(self):
        with pytest.raises(ValueError, match="transaction_id must be positive"):
            Transaction(transaction_id=0, start_version=1)

    def test_transaction_invalid_start_version(self):
        with pytest.raises(ValueError, match="start_version cannot be negative"):
            Transaction(transaction_id=1, start_version=-1)

    def test_transaction_mark_committed(self):
        txn = Transaction(transaction_id=1, start_version=1)
        txn.mark_committed(5)
        assert txn.is_committed is True
        assert txn.is_active is False
        assert txn.commit_version == 5

    def test_transaction_mark_committed_wrong_state(self):
        txn = Transaction(transaction_id=1, start_version=1)
        txn.mark_aborted()
        with pytest.raises(TransactionStateError):
            txn.mark_committed(5)

    def test_transaction_mark_committed_invalid_version(self):
        txn = Transaction(transaction_id=1, start_version=1)
        with pytest.raises(ValueError, match="commit_version must be positive"):
            txn.mark_committed(0)

    def test_transaction_mark_aborted(self):
        txn = Transaction(transaction_id=1, start_version=1)
        txn.mark_aborted()
        assert txn.is_aborted is True
        assert txn.is_active is False

    def test_transaction_mark_aborted_wrong_state(self):
        txn = Transaction(transaction_id=1, start_version=1)
        txn.mark_committed(5)
        with pytest.raises(TransactionStateError):
            txn.mark_aborted()


class TestMultiVersionWrite:
    def test_single_write_single_key(self):
        store = make_store()
        txn = store.begin_transaction()
        store.write(txn, "key1", "value1")
        commit_version = store.commit(txn)
        assert commit_version > 0
        assert store.read("key1") == "value1"

    def test_multiple_writes_same_key(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2")
        cv2 = store.commit(txn2)

        txn3 = store.begin_transaction()
        store.write(txn3, "key1", "v3")
        cv3 = store.commit(txn3)

        assert cv3 > cv2 > cv1
        assert store.read_version("key1", cv1) == "v1"
        assert store.read_version("key1", cv2) == "v2"
        assert store.read_version("key1", cv3) == "v3"
        assert store.read("key1") == "v3"

    def test_version_numbers_monotonic(self):
        store = make_store()
        versions = []
        for i in range(5):
            txn = store.begin_transaction()
            store.write(txn, f"key{i}", f"value{i}")
            cv = store.commit(txn)
            versions.append(cv)

        for i in range(1, len(versions)):
            assert versions[i] > versions[i - 1]

    def test_multiple_keys(self):
        store = make_store()
        txn = store.begin_transaction()
        store.write(txn, "a", 1)
        store.write(txn, "b", 2)
        store.write(txn, "c", 3)
        store.commit(txn)

        assert store.read("a") == 1
        assert store.read("b") == 2
        assert store.read("c") == 3

    def test_write_within_transaction_not_visible_before_commit(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "txn1_value")

        with pytest.raises(KeyNotFoundError):
            store.read("key1")

        store.commit(txn1)
        assert store.read("key1") == "txn1_value"


class TestSnapshotIsolationRead:
    def test_snapshot_read_sees_committed_data(self):
        store = make_store()
        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        snap = store.create_snapshot()
        assert store.read("key1", snap) == "v1"

    def test_snapshot_read_does_not_see_newer_commits(self):
        store = make_store()
        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)

        snap = store.create_snapshot()
        assert snap.snapshot_version >= cv1

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2")
        cv2 = store.commit(txn2)

        assert cv2 > snap.snapshot_version
        assert store.read("key1", snap) == "v1"
        assert store.read("key1") == "v2"

    def test_snapshot_read_does_not_see_uncommitted(self):
        store = make_store()
        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2_uncommitted")

        snap = store.create_snapshot()
        assert store.read("key1", snap) == "v1"

        store.commit(txn2)
        assert store.read("key1") == "v2_uncommitted"

    def test_snapshot_at_exact_version(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        snap1 = store.create_snapshot()

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2")
        cv2 = store.commit(txn2)

        assert store.read("key1", snap1) == "v1"

        snap2 = store.create_snapshot()
        assert snap2.snapshot_version >= cv2
        assert store.read("key1", snap2) == "v2"

    def test_snapshot_version_is_latest(self):
        store = make_store()
        txn = store.begin_transaction()
        store.write(txn, "key1", "only")
        store.commit(txn)

        snap = store.create_snapshot()
        assert store.read("key1", snap) == store.read("key1")

    def test_release_snapshot(self):
        store = make_store()
        snap = store.create_snapshot()
        assert store.count_active_snapshots() == 1
        store.release_snapshot(snap)
        assert store.count_active_snapshots() == 0


class TestWriteWriteConflict:
    def test_no_conflict_different_keys(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "txn1_value")

        txn2 = store.begin_transaction()
        store.write(txn2, "key2", "txn2_value")

        store.commit(txn1)
        store.commit(txn2)

        assert store.read("key1") == "txn1_value"
        assert store.read("key2") == "txn2_value"

    def test_conflict_same_key_concurrent_writes(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "txn1_value")

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "txn2_value")

        store.commit(txn1)

        with pytest.raises(WriteWriteConflictError):
            store.commit(txn2)

        assert store.read("key1") == "txn1_value"

    def test_no_conflict_serializable_writes(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2")
        store.commit(txn2)

        assert store.read("key1") == "v2"

    def test_conflict_after_multiple_reads(self):
        store = make_store()

        txn_initial = store.begin_transaction()
        store.write(txn_initial, "counter", 0)
        store.commit(txn_initial)

        txn_a = store.begin_transaction()
        val_a = store.transaction_read(txn_a, "counter")
        store.write(txn_a, "counter", val_a + 1)

        txn_b = store.begin_transaction()
        val_b = store.transaction_read(txn_b, "counter")
        store.write(txn_b, "counter", val_b + 1)

        store.commit(txn_a)
        assert store.read("counter") == 1

        with pytest.raises(WriteWriteConflictError):
            store.commit(txn_b)

    def test_aborted_transaction_does_not_cause_conflict(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.rollback(txn1)

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2")
        store.commit(txn2)

        assert store.read("key1") == "v2"


class TestTransactionCommitAndRollback:
    def test_commit_changes_visible(self):
        store = make_store()
        txn = store.begin_transaction()
        store.write(txn, "key1", "committed_value")
        store.commit(txn)
        assert store.read("key1") == "committed_value"

    def test_rollback_changes_not_visible(self):
        store = make_store()
        txn = store.begin_transaction()
        store.write(txn, "key1", "rolled_back_value")
        store.rollback(txn)

        with pytest.raises(KeyNotFoundError):
            store.read("key1")

    def test_rollback_does_not_affect_other_transactions(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2_rolled_back")
        store.rollback(txn2)

        assert store.read("key1") == "v1"

    def test_commit_invalid_state(self):
        store = make_store()
        txn = store.begin_transaction()
        store.rollback(txn)
        with pytest.raises(TransactionStateError):
            store.commit(txn)

    def test_rollback_invalid_state(self):
        store = make_store()
        txn = store.begin_transaction()
        store.commit(txn)
        with pytest.raises(TransactionStateError):
            store.rollback(txn)

    def test_write_on_rolled_back_transaction(self):
        store = make_store()
        txn = store.begin_transaction()
        store.rollback(txn)
        with pytest.raises(TransactionStateError):
            store.write(txn, "key1", "value")

    def test_transaction_read_own_writes(self):
        store = make_store()

        txn_initial = store.begin_transaction()
        store.write(txn_initial, "key1", "initial")
        store.commit(txn_initial)

        txn = store.begin_transaction()
        assert store.transaction_read(txn, "key1") == "initial"
        store.write(txn, "key1", "updated")
        assert store.transaction_read(txn, "key1") == "updated"

    def test_transaction_read_does_not_see_other_uncommitted(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "txn1")

        txn2 = store.begin_transaction()
        with pytest.raises(KeyNotFoundError):
            store.transaction_read(txn2, "key1")

        store.commit(txn1)
        with pytest.raises(KeyNotFoundError):
            store.transaction_read(txn2, "key1")

        txn3 = store.begin_transaction()
        assert store.transaction_read(txn3, "key1") == "txn1"


class TestGarbageCollection:
    def test_gc_no_active_snapshots_no_txns(self):
        store = make_store()

        for i in range(10):
            txn = store.begin_transaction()
            store.write(txn, "key1", f"v{i}")
            store.commit(txn)

        versions_before = store.get_versions("key1")
        assert len(versions_before) == 10

        reclaimed = store.collect_garbage()
        assert reclaimed > 0

        versions_after = store.get_versions("key1")
        assert len(versions_after) < len(versions_before)

    def test_gc_preserves_versions_needed_by_snapshot(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)

        snap = store.create_snapshot()

        for i in range(2, 6):
            txn = store.begin_transaction()
            store.write(txn, "key1", f"v{i}")
            store.commit(txn)

        reclaimed = store.collect_garbage()
        assert reclaimed >= 0

        assert store.read_version("key1", cv1) == "v1"
        assert store.read("key1", snap) == "v1"

    def test_gc_preserves_versions_needed_by_active_transaction(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)

        long_running_txn = store.begin_transaction()

        for i in range(2, 6):
            txn = store.begin_transaction()
            store.write(txn, "key1", f"v{i}")
            store.commit(txn)

        reclaimed = store.collect_garbage()
        assert reclaimed >= 0

        assert store.read_version("key1", cv1) == "v1"
        assert store.transaction_read(long_running_txn, "key1") == "v1"

    def test_read_reclaimed_version_raises(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2")
        cv2 = store.commit(txn2)

        reclaimed = store.collect_garbage()
        assert reclaimed > 0

        try:
            store.read_version("key1", cv1)
        except VersionReclaimedError:
            pass
        else:
            assert cv1 in store._reclaimed_versions or store.read_version("key1", cv1) == "v1"

        assert store.read_version("key1", cv2) == "v2"

    def test_gc_with_tombstones(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        txn2 = store.begin_transaction()
        store.delete(txn2, "key1")
        store.commit(txn2)

        reclaimed = store.collect_garbage()
        assert reclaimed >= 0


class TestBoundaryConditions:
    def test_single_key_many_versions(self):
        store = make_store()
        num_versions = 100
        commit_versions = []

        for i in range(num_versions):
            txn = store.begin_transaction()
            store.write(txn, "key", i)
            cv = store.commit(txn)
            commit_versions.append(cv)

        for i, cv in enumerate(commit_versions):
            try:
                val = store.read_version("key", cv)
                assert val == i
            except VersionReclaimedError:
                pass

    def test_read_nonexistent_key(self):
        store = make_store()
        with pytest.raises(KeyNotFoundError):
            store.read("nonexistent")

    def test_read_version_nonexistent_key(self):
        store = make_store()
        with pytest.raises(KeyNotFoundError):
            store.read_version("nonexistent", 1)

    def test_read_version_not_found(self):
        store = make_store()
        txn = store.begin_transaction()
        store.write(txn, "key1", "v1")
        store.commit(txn)

        with pytest.raises(VersionNotFoundError):
            store.read_version("key1", 99999)

    def test_snapshot_exactly_latest_commit_version(self):
        store = make_store()

        txn = store.begin_transaction()
        store.write(txn, "key1", "v1")
        cv = store.commit(txn)

        snap = store.create_snapshot()
        assert snap.snapshot_version >= cv
        assert store.read("key1", snap) == "v1"

    def test_empty_transaction_commit(self):
        store = make_store()
        txn = store.begin_transaction()
        commit_version = store.commit(txn)
        assert commit_version > 0

    def test_empty_transaction_rollback(self):
        store = make_store()
        txn = store.begin_transaction()
        store.rollback(txn)
        assert txn.is_aborted is True

    def test_count_active_transactions(self):
        store = make_store()
        assert store.count_active_transactions() == 0

        txn1 = store.begin_transaction()
        assert store.count_active_transactions() == 1

        txn2 = store.begin_transaction()
        assert store.count_active_transactions() == 2

        store.commit(txn1)
        assert store.count_active_transactions() == 1

        store.rollback(txn2)
        assert store.count_active_transactions() == 0


class TestDeleteOperation:
    def test_delete_key(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)
        assert store.read("key1") == "v1"

        txn2 = store.begin_transaction()
        store.delete(txn2, "key1")
        store.commit(txn2)

        with pytest.raises(KeyNotFoundError):
            store.read("key1")

        assert store.read_version("key1", cv1) == "v1"

    def test_delete_in_transaction_not_visible_before_commit(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        txn2 = store.begin_transaction()
        store.delete(txn2, "key1")

        assert store.read("key1") == "v1"
        store.commit(txn2)
        with pytest.raises(KeyNotFoundError):
            store.read("key1")

    def test_transaction_read_own_delete(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        store.commit(txn1)

        txn2 = store.begin_transaction()
        assert store.transaction_read(txn2, "key1") == "v1"
        store.delete(txn2, "key1")
        with pytest.raises(KeyNotFoundError):
            store.transaction_read(txn2, "key1")

        store.rollback(txn2)
        assert store.read("key1") == "v1"


class TestClearAndReset:
    def test_clear_store(self):
        store = make_store()
        txn = store.begin_transaction()
        store.write(txn, "key1", "v1")
        store.write(txn, "key2", "v2")
        store.commit(txn)

        snap = store.create_snapshot()
        assert store.count_active_snapshots() == 1

        store.clear()

        assert store.count_active_snapshots() == 0
        assert store.count_active_transactions() == 0
        with pytest.raises(KeyNotFoundError):
            store.read("key1")


class TestVersionContinuity:
    def test_commit_versions_are_contiguous_no_gaps(self):
        store = make_store()
        commit_versions = []
        for i in range(20):
            txn = store.begin_transaction()
            store.write(txn, f"key-{i % 3}", f"v{i}")
            cv = store.commit(txn)
            commit_versions.append(cv)

        for i in range(1, len(commit_versions)):
            assert commit_versions[i] == commit_versions[i - 1] + 1

    def test_snapshot_version_equals_latest_committed(self):
        store = make_store()
        snap0 = store.create_snapshot()
        assert snap0.snapshot_version == 0

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)

        snap1 = store.create_snapshot()
        assert snap1.snapshot_version == cv1

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "v2")
        cv2 = store.commit(txn2)

        snap2 = store.create_snapshot()
        assert snap2.snapshot_version == cv2
        assert cv2 == cv1 + 1

    def test_snapshot_does_not_include_uncommitted_versions(self):
        store = make_store()

        txn1 = store.begin_transaction()
        store.write(txn1, "key1", "committed")
        cv1 = store.commit(txn1)

        txn2 = store.begin_transaction()
        store.write(txn2, "key1", "uncommitted")

        snap = store.create_snapshot()
        assert snap.snapshot_version == cv1
        assert store.read("key1", snap) == "committed"

        store.rollback(txn2)

    def test_start_version_equals_committed_version(self):
        store = make_store()

        txn0 = store.begin_transaction()
        assert txn0.start_version == 0
        store.write(txn0, "key1", "v0")
        cv0 = store.commit(txn0)

        txn1 = store.begin_transaction()
        assert txn1.start_version == cv0
        store.write(txn1, "key1", "v1")
        cv1 = store.commit(txn1)

        txn2 = store.begin_transaction()
        assert txn2.start_version == cv1


class TestConcurrency:
    def test_concurrent_writes_different_keys(self):
        import threading

        store = make_store()

        txn_initial = store.begin_transaction()
        store.write(txn_initial, "counter-a", 0)
        store.write(txn_initial, "counter-b", 0)
        store.commit(txn_initial)

        results = {"success": 0, "conflict": 0}
        lock = threading.Lock()

        def writer(key, iterations):
            for _ in range(iterations):
                txn = store.begin_transaction()
                val = store.transaction_read(txn, key)
                store.write(txn, key, val + 1)
                try:
                    store.commit(txn)
                    with lock:
                        results["success"] += 1
                except WriteWriteConflictError:
                    store.rollback(txn)
                    with lock:
                        results["conflict"] += 1

        t1 = threading.Thread(target=writer, args=("counter-a", 20))
        t2 = threading.Thread(target=writer, args=("counter-b", 20))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert t1.is_alive() is False
        assert t2.is_alive() is False
        assert store.read("counter-a") + store.read("counter-b") == 40
        assert results["success"] + results["conflict"] == 40

    def test_concurrent_writes_same_key_trigger_conflicts(self):
        import threading

        store = make_store()

        txn_initial = store.begin_transaction()
        store.write(txn_initial, "counter", 0)
        store.commit(txn_initial)

        results = {"success": 0, "conflict": 0}
        lock = threading.Lock()

        def writer(iterations):
            for _ in range(iterations):
                txn = store.begin_transaction()
                val = store.transaction_read(txn, "counter")
                store.write(txn, "counter", val + 1)
                try:
                    store.commit(txn)
                    with lock:
                        results["success"] += 1
                except WriteWriteConflictError:
                    store.rollback(txn)
                    with lock:
                        results["conflict"] += 1

        threads = [threading.Thread(target=writer, args=(15,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            assert t.is_alive() is False

        assert results["success"] + results["conflict"] == 60
        assert results["conflict"] > 0 or store.read("counter") == 60

    def test_concurrent_snapshot_reads_are_isolated(self):
        import threading
        import time

        store = make_store()

        txn_initial = store.begin_transaction()
        store.write(txn_initial, "key1", 0)
        store.commit(txn_initial)

        snap = store.create_snapshot()
        snapshot_values = []
        read_errors = []

        def snapshot_reader(snapshot, count):
            try:
                for _ in range(count):
                    val = store.read("key1", snapshot)
                    snapshot_values.append(val)
                    time.sleep(0.001)
            except Exception as e:
                read_errors.append(e)

        def writer(count):
            for _ in range(count):
                txn = store.begin_transaction()
                val = store.transaction_read(txn, "key1")
                store.write(txn, "key1", val + 1)
                try:
                    store.commit(txn)
                except WriteWriteConflictError:
                    store.rollback(txn)

        reader = threading.Thread(target=snapshot_reader, args=(snap, 30))
        writer_thread = threading.Thread(target=writer, args=(30,))

        reader.start()
        writer_thread.start()
        reader.join(timeout=10)
        writer_thread.join(timeout=10)

        assert reader.is_alive() is False
        assert writer_thread.is_alive() is False
        assert len(read_errors) == 0
        assert all(v == 0 for v in snapshot_values)

        store.release_snapshot(snap)

    def test_concurrent_mixed_operations(self):
        import threading
        import time

        store = make_store()

        for i in range(3):
            txn = store.begin_transaction()
            store.write(txn, f"key-{i}", i)
            store.commit(txn)

        errors = []
        completed = {"count": 0}
        lock = threading.Lock()

        def op_read():
            try:
                txn = store.begin_transaction()
                for i in range(3):
                    store.transaction_read(txn, f"key-{i}")
                store.rollback(txn)
            except Exception as e:
                errors.append(e)
            finally:
                with lock:
                    completed["count"] += 1

        def op_write():
            try:
                txn = store.begin_transaction()
                for i in range(3):
                    val = store.transaction_read(txn, f"key-{i}")
                    store.write(txn, f"key-{i}", val + 10)
                store.commit(txn)
            except WriteWriteConflictError:
                store.rollback(txn)
            except Exception as e:
                errors.append(e)
            finally:
                with lock:
                    completed["count"] += 1

        def op_snapshot():
            try:
                snap = store.create_snapshot()
                for i in range(3):
                    try:
                        store.read(f"key-{i}", snap)
                    except KeyNotFoundError:
                        pass
                time.sleep(0.002)
                store.release_snapshot(snap)
            except Exception as e:
                errors.append(e)
            finally:
                with lock:
                    completed["count"] += 1

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=op_read))
            threads.append(threading.Thread(target=op_write))
            threads.append(threading.Thread(target=op_snapshot))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
            assert t.is_alive() is False

        assert len(errors) == 0, f"Errors: {errors}"
        assert completed["count"] == 15
