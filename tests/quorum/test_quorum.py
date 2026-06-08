import pytest

from solocoder_py.quorum import (
    InvalidQuorumConfigError,
    QuorumCoordinator,
    QuorumReadError,
    QuorumWriteError,
    Replica,
    ReplicaStatus,
    ReplicaUnreachableError,
    StoredValue,
    VersionConflictError,
)
from .conftest import make_coordinator, make_replica, make_replicas


class TestQuorumConfigValidation:
    def test_valid_config_3_2_2(self):
        replicas = make_replicas(3)
        coord = QuorumCoordinator(replicas=replicas, w=2, r=2)
        assert coord.n == 3
        assert coord.w == 2
        assert coord.r == 2

    def test_valid_config_5_3_3(self):
        replicas = make_replicas(5)
        coord = QuorumCoordinator(replicas=replicas, w=3, r=3)
        assert coord.n == 5
        assert coord.w == 3
        assert coord.r == 3

    def test_valid_minimal_overlap_w_r_equals_n_plus_1(self):
        replicas = make_replicas(3)
        coord = QuorumCoordinator(replicas=replicas, w=2, r=2)
        assert coord.w + coord.r == coord.n + 1

    def test_invalid_zero_replicas(self):
        with pytest.raises(InvalidQuorumConfigError):
            QuorumCoordinator(replicas=[], w=1, r=1)

    def test_invalid_w_zero(self):
        replicas = make_replicas(3)
        with pytest.raises(InvalidQuorumConfigError):
            QuorumCoordinator(replicas=replicas, w=0, r=2)

    def test_invalid_r_zero(self):
        replicas = make_replicas(3)
        with pytest.raises(InvalidQuorumConfigError):
            QuorumCoordinator(replicas=replicas, w=2, r=0)

    def test_invalid_w_greater_than_n(self):
        replicas = make_replicas(3)
        with pytest.raises(InvalidQuorumConfigError):
            QuorumCoordinator(replicas=replicas, w=4, r=2)

    def test_invalid_r_greater_than_n(self):
        replicas = make_replicas(3)
        with pytest.raises(InvalidQuorumConfigError):
            QuorumCoordinator(replicas=replicas, w=2, r=4)

    def test_invalid_w_plus_r_not_greater_than_n(self):
        replicas = make_replicas(3)
        with pytest.raises(InvalidQuorumConfigError):
            QuorumCoordinator(replicas=replicas, w=1, r=1)


class TestReplicaBasics:
    def test_replica_initial_status_online(self):
        r = make_replica()
        assert r.status == ReplicaStatus.ONLINE

    def test_replica_mark_unreachable(self):
        r = make_replica()
        r.mark_unreachable()
        assert r.status == ReplicaStatus.UNREACHABLE
        with pytest.raises(ReplicaUnreachableError):
            r.read("key")

    def test_replica_mark_online_after_unreachable(self):
        r = make_replica()
        r.mark_unreachable()
        r.mark_online()
        assert r.status == ReplicaStatus.ONLINE
        assert r.read("nonexistent") is None

    def test_replica_write_and_read(self):
        r = make_replica()
        ok = r.write("k1", "v1", 1)
        assert ok is True
        stored = r.read("k1")
        assert stored is not None
        assert stored.value == "v1"
        assert stored.version == 1

    def test_replica_write_lower_version_rejected(self):
        r = make_replica()
        r.write("k1", "v2", 2)
        ok = r.write("k1", "v1", 1)
        assert ok is False
        stored = r.read("k1")
        assert stored.version == 2
        assert stored.value == "v2"

    def test_replica_write_same_version_overwrites(self):
        r = make_replica()
        r.write("k1", "v1", 1)
        ok = r.write("k1", "v2", 1)
        assert ok is True
        stored = r.read("k1")
        assert stored.value == "v2"

    def test_replica_get_version(self):
        r = make_replica()
        assert r.get_version("k1") == 0
        r.write("k1", "v1", 5)
        assert r.get_version("k1") == 5

    def test_replica_stats(self):
        r = make_replica()
        r.write("k1", "v1", 1)
        r.read("k1")
        r.read("nonexistent")
        stats = r.get_stats()
        assert stats.replica_id == r.id
        assert stats.status == ReplicaStatus.ONLINE
        assert stats.keys_count == 1
        assert stats.total_writes == 1
        assert stats.successful_writes == 1
        assert stats.total_reads == 2
        assert stats.successful_reads == 2
        assert stats.write_success_rate == 1.0
        assert stats.read_success_rate == 1.0

    def test_replica_fail_writes(self):
        r = make_replica()
        r.set_fail_writes(True)
        ok = r.write("k1", "v1", 1)
        assert ok is False
        assert r.get_version("k1") == 0

    def test_replica_fail_reads(self):
        r = make_replica()
        r.write("k1", "v1", 1)
        r.set_fail_reads(True)
        with pytest.raises(ReplicaUnreachableError):
            r.read("k1")

    def test_replica_reset_stats(self):
        r = make_replica()
        r.write("k1", "v1", 1)
        r.read("k1")
        r.reset_stats()
        stats = r.get_stats()
        assert stats.total_reads == 0
        assert stats.total_writes == 0
        assert stats.keys_count == 1


class TestQuorumWriteSuccess:
    def test_write_all_replicas_succeed(self):
        coord = make_coordinator(n=3, w=2, r=2)
        result = coord.write("k1", "v1")
        assert result.success is True
        assert result.key == "k1"
        assert result.value == "v1"
        assert result.version == 1
        assert len(result.successful_replicas) == 3
        assert len(result.failed_replicas) == 0
        for replica in coord.replicas:
            stored = replica.read("k1")
            assert stored is not None
            assert stored.value == "v1"
            assert stored.version == 1

    def test_write_version_increments(self):
        coord = make_coordinator(n=3, w=2, r=2)
        r1 = coord.write("k1", "v1")
        assert r1.version == 1
        r2 = coord.write("k1", "v2")
        assert r2.version == 2
        r3 = coord.write("k1", "v3")
        assert r3.version == 3

    def test_write_exactly_w_replicas_succeed(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.replicas[2].set_fail_writes(True)
        result = coord.write("k1", "v1")
        assert len(result.successful_replicas) == 2
        assert len(result.failed_replicas) == 1
        assert coord.replicas[0].get_version("k1") == 1
        assert coord.replicas[1].get_version("k1") == 1
        assert coord.replicas[2].get_version("k1") == 0

    def test_write_minimal_overlap_config(self):
        coord = make_coordinator(n=5, w=3, r=3)
        result = coord.write("k1", "v1")
        assert result.success is True
        assert result.version == 1


class TestQuorumWriteFailure:
    def test_write_less_than_w_fails(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.replicas[1].set_fail_writes(True)
        coord.replicas[2].set_fail_writes(True)
        with pytest.raises(QuorumWriteError) as exc_info:
            coord.write("k1", "v1")
        assert exc_info.value.key == "k1"
        assert exc_info.value.successful == 1
        assert exc_info.value.required == 2

    def test_write_all_replicas_fail(self):
        coord = make_coordinator(n=3, w=2, r=2)
        for r in coord.replicas:
            r.set_fail_writes(True)
        with pytest.raises(QuorumWriteError):
            coord.write("k1", "v1")

    def test_write_with_unreachable_replicas(self):
        coord = make_coordinator(n=3, w=3, r=2)
        coord.mark_replica_unreachable(coord.replicas[0].id)
        with pytest.raises(QuorumWriteError):
            coord.write("k1", "v1")


class TestQuorumReadSuccess:
    def test_read_existing_key(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        result = coord.read("k1")
        assert result.success is True
        assert result.key == "k1"
        assert result.value == "v1"
        assert result.version == 1
        assert len(result.successful_replicas) == 3

    def test_read_nonexistent_key(self):
        coord = make_coordinator(n=3, w=2, r=2)
        result = coord.read("nonexistent")
        assert result.success is True
        assert result.value is None
        assert result.version == 0

    def test_read_exactly_r_replicas_respond(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.replicas[2].mark_unreachable()
        result = coord.read("k1")
        assert result.success is True
        assert len(result.successful_replicas) == 2
        assert len(result.failed_replicas) == 1
        assert result.value == "v1"

    def test_read_highest_version_wins(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.write("k1", "v2")
        result = coord.read("k1")
        assert result.value == "v2"
        assert result.version == 2

    def test_read_minimal_overlap_config(self):
        coord = make_coordinator(n=5, w=3, r=3)
        coord.write("k1", "v1")
        for i in range(2):
            coord.replicas[i].mark_unreachable()
        result = coord.read("k1")
        assert result.success is True
        assert len(result.successful_replicas) == 3


class TestQuorumReadFailure:
    def test_read_less_than_r_fails(self):
        coord = make_coordinator(n=3, w=2, r=3)
        coord.write("k1", "v1")
        coord.replicas[0].mark_unreachable()
        coord.replicas[1].mark_unreachable()
        with pytest.raises(QuorumReadError) as exc_info:
            coord.read("k1")
        assert exc_info.value.key == "k1"
        assert exc_info.value.successful == 1
        assert exc_info.value.required == 3

    def test_read_all_replicas_unreachable(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        for r in coord.replicas:
            r.mark_unreachable()
        with pytest.raises(QuorumReadError):
            coord.read("k1")


class TestReadRepair:
    def test_read_repair_fixes_stale_replica(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.write("k1", "v2")
        coord.replicas[2].set_fail_writes(True)
        coord.write("k1", "v3")
        coord.replicas[2].set_fail_writes(False)
        assert coord.replicas[2].get_version("k1") == 2
        result = coord.read("k1", perform_repair=True)
        assert result.conflict_detected is True
        assert result.value == "v3"
        assert result.version == 3
        assert coord.replicas[2].get_version("k1") == 3
        assert coord.replicas[2].read("k1").value == "v3"
        assert len(result.repaired_replicas) >= 1

    def test_read_without_repair_leaves_stale(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.write("k1", "v2")
        coord.replicas[2].set_fail_writes(True)
        coord.write("k1", "v3")
        coord.replicas[2].set_fail_writes(False)
        result = coord.read("k1", perform_repair=False)
        assert result.conflict_detected is True
        assert coord.replicas[2].get_version("k1") == 2
        assert len(result.repaired_replicas) == 0

    def test_read_repair_missing_replica(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.replicas[2].set_fail_writes(True)
        coord.write("k1", "v1")
        coord.replicas[2].set_fail_writes(False)
        assert coord.replicas[2].read("k1") is None
        result = coord.read("k1")
        assert len(result.repaired_replicas) >= 1
        assert coord.replicas[2].id in result.repaired_replicas
        assert coord.replicas[2].read("k1") is not None
        assert coord.replicas[2].read("k1").value == "v1"


class TestVersionConflictResolution:
    def test_resolve_conflict_picks_highest_version(self):
        replicas = make_replicas(3)
        replicas[0].write("k1", "v1", 1)
        replicas[1].write("k1", "v3", 3)
        replicas[2].write("k1", "v2", 2)
        coord = QuorumCoordinator(replicas=replicas, w=2, r=2)
        winner = coord.resolve_conflict("k1")
        assert winner is not None
        assert winner.value == "v3"
        assert winner.version == 3

    def test_resolve_conflict_propagates_winner(self):
        replicas = make_replicas(3)
        replicas[0].write("k1", "v1", 1)
        replicas[1].write("k1", "v3", 3)
        replicas[2].write("k1", "v2", 2)
        coord = QuorumCoordinator(replicas=replicas, w=2, r=2)
        coord.resolve_conflict("k1")
        for r in coord.replicas:
            stored = r.read("k1")
            assert stored is not None
            assert stored.version == 3
            assert stored.value == "v3"

    def test_resolve_conflict_no_key_returns_none(self):
        coord = make_coordinator(n=3, w=2, r=2)
        result = coord.resolve_conflict("nonexistent")
        assert result is None

    def test_resolve_conflict_raise_on_conflict(self):
        replicas = make_replicas(3)
        replicas[0].write("k1", "v1", 1)
        replicas[1].write("k1", "v2", 2)
        coord = QuorumCoordinator(replicas=replicas, w=2, r=2)
        with pytest.raises(VersionConflictError):
            coord.resolve_conflict("k1", raise_on_conflict=True)

    def test_resolve_conflict_same_version_no_raise(self):
        replicas = make_replicas(3)
        replicas[0].write("k1", "v1", 2)
        replicas[1].write("k1", "v1", 2)
        coord = QuorumCoordinator(replicas=replicas, w=2, r=2)
        winner = coord.resolve_conflict("k1", raise_on_conflict=True)
        assert winner is not None
        assert winner.version == 2


class TestReplicaStatusAndStats:
    def test_get_all_replica_stats(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.read("k1")
        stats_list = coord.get_all_replica_stats()
        assert len(stats_list) == 3
        for stats in stats_list:
            assert stats.status == ReplicaStatus.ONLINE
            assert stats.total_writes >= 1
            assert stats.total_reads >= 1

    def test_get_replica_stats_by_id(self):
        coord = make_coordinator(n=3, w=2, r=2)
        target_id = coord.replicas[1].id
        stats = coord.get_replica_stats(target_id)
        assert stats is not None
        assert stats.replica_id == target_id

    def test_get_replica_stats_nonexistent(self):
        coord = make_coordinator(n=3, w=2, r=2)
        assert coord.get_replica_stats("nonexistent") is None

    def test_mark_replica_unreachable(self):
        coord = make_coordinator(n=3, w=2, r=2)
        rid = coord.replicas[0].id
        ok = coord.mark_replica_unreachable(rid)
        assert ok is True
        assert coord.get_replica_stats(rid).status == ReplicaStatus.UNREACHABLE

    def test_mark_replica_unreachable_nonexistent(self):
        coord = make_coordinator(n=3, w=2, r=2)
        ok = coord.mark_replica_unreachable("nonexistent")
        assert ok is False

    def test_mark_replica_online(self):
        coord = make_coordinator(n=3, w=2, r=2)
        rid = coord.replicas[0].id
        coord.mark_replica_unreachable(rid)
        ok = coord.mark_replica_online(rid)
        assert ok is True
        assert coord.get_replica_stats(rid).status == ReplicaStatus.ONLINE

    def test_get_replica(self):
        coord = make_coordinator(n=3, w=2, r=2)
        rid = coord.replicas[1].id
        replica = coord.get_replica(rid)
        assert replica is not None
        assert replica.id == rid

    def test_get_all_data_across_replicas(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.write("k2", "v2")
        all_data = coord.get_all_data_across_replicas()
        assert len(all_data) == 3
        for rid, data in all_data.items():
            assert "k1" in data
            assert "k2" in data
            assert data["k1"].value == "v1"
            assert data["k2"].value == "v2"


class TestDegradedModeWithUnreachableReplicas:
    def test_write_succeeds_with_some_unreachable(self):
        coord = make_coordinator(n=5, w=3, r=3)
        coord.mark_replica_unreachable(coord.replicas[0].id)
        coord.mark_replica_unreachable(coord.replicas[1].id)
        result = coord.write("k1", "v1")
        assert result.success is True
        assert len(result.successful_replicas) == 3

    def test_read_succeeds_with_some_unreachable(self):
        coord = make_coordinator(n=5, w=3, r=3)
        coord.write("k1", "v1")
        coord.mark_replica_unreachable(coord.replicas[0].id)
        coord.mark_replica_unreachable(coord.replicas[1].id)
        result = coord.read("k1")
        assert result.success is True
        assert result.value == "v1"

    def test_write_fails_when_too_many_unreachable(self):
        coord = make_coordinator(n=3, w=3, r=2)
        coord.mark_replica_unreachable(coord.replicas[0].id)
        with pytest.raises(QuorumWriteError):
            coord.write("k1", "v1")

    def test_read_fails_when_too_many_unreachable(self):
        coord = make_coordinator(n=3, w=2, r=3)
        coord.write("k1", "v1")
        coord.mark_replica_unreachable(coord.replicas[0].id)
        with pytest.raises(QuorumReadError):
            coord.read("k1")

    def test_unreachable_replica_skipped_in_repair(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.replicas[2].set_fail_writes(True)
        coord.write("k1", "v2")
        coord.replicas[2].set_fail_writes(False)
        assert coord.replicas[0].get_version("k1") == 2
        assert coord.replicas[1].get_version("k1") == 2
        assert coord.replicas[2].get_version("k1") == 1
        coord.mark_replica_unreachable(coord.replicas[2].id)
        result = coord.read("k1")
        assert len(result.repaired_replicas) == 0
        assert coord.replicas[2].get_version("k1") == 1
        assert coord.replicas[2].status == ReplicaStatus.UNREACHABLE
        assert coord.replicas[2].id not in result.repaired_replicas
        assert coord.replicas[2].id in result.failed_replicas


class TestEdgeCases:
    def test_multiple_keys_version_independence(self):
        coord = make_coordinator(n=3, w=2, r=2)
        coord.write("k1", "v1")
        coord.write("k2", "v2")
        coord.write("k1", "v1b")
        r1 = coord.read("k1")
        r2 = coord.read("k2")
        assert r1.version == 2
        assert r2.version == 1

    def test_explicit_version_write(self):
        coord = make_coordinator(n=3, w=2, r=2)
        result = coord.write("k1", "v1", version=10)
        assert result.version == 10
        for r in coord.replicas:
            assert r.get_version("k1") == 10

    def test_write_then_read_then_write_versions(self):
        coord = make_coordinator(n=3, w=2, r=2)
        w1 = coord.write("k", "a")
        assert w1.version == 1
        coord.read("k")
        w2 = coord.write("k", "b")
        assert w2.version == 2
        r = coord.read("k")
        assert r.version == 2
        assert r.value == "b"

    def test_5_replicas_w3_r3_exactly_quorum(self):
        coord = make_coordinator(n=5, w=3, r=3)
        coord.replicas[3].set_fail_writes(True)
        coord.replicas[4].set_fail_writes(True)
        w = coord.write("k", "val")
        assert len(w.successful_replicas) == 3
        coord.replicas[3].set_fail_writes(False)
        coord.replicas[4].set_fail_writes(False)
        coord.mark_replica_unreachable(coord.replicas[0].id)
        coord.mark_replica_unreachable(coord.replicas[1].id)
        r = coord.read("k")
        assert len(r.successful_replicas) == 3
        assert r.value == "val"
