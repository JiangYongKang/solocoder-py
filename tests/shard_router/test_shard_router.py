from __future__ import annotations

import pytest

from solocoder_py.shard_router import (
    DEFAULT_SLOT_COUNT,
    MigrationProgress,
    NodeHasMigrationsError,
    NodeNotEmptyError,
    NodeNotFoundError,
    RedirectRequiredError,
    RouteResult,
    RouterSnapshot,
    ShardNode,
    ShardRouter,
    SlotAlreadyAssignedError,
    SlotAssignment,
    SlotMigrationInProgressError,
    SlotNotAssignedError,
    SlotNotMigratingError,
    SlotNotRoutedError,
    SlotRange,
    SlotRangeInvalidError,
    WriteResult,
    WriteStatus,
)


def find_key_for_slot(target_slot: int, total_slots: int = DEFAULT_SLOT_COUNT) -> str:
    for i in range(200000):
        key = f"testkey-{i}"
        if ShardRouter.key_to_slot(key, total_slots) == target_slot:
            return key
    for i in range(200000):
        key = f"{{tag-{i}}}:suffix"
        if ShardRouter.key_to_slot(key, total_slots) == target_slot:
            return key
    raise RuntimeError(f"Could not find key mapping to slot {target_slot}")



class TestSlotRange:
    def test_slot_range_contains(self):
        r = SlotRange(start=10, end=20)
        assert r.contains(10)
        assert r.contains(15)
        assert r.contains(20)
        assert not r.contains(9)
        assert not r.contains(21)

    def test_slot_range_to_list(self):
        r = SlotRange(start=0, end=3)
        assert r.to_list() == [0, 1, 2, 3]

    def test_slot_range_invalid(self):
        with pytest.raises(ValueError):
            SlotRange(start=5, end=3)


class TestKeyToSlot:
    def test_key_to_slot_deterministic(self):
        slot1 = ShardRouter.key_to_slot("user:1001")
        slot2 = ShardRouter.key_to_slot("user:1001")
        assert slot1 == slot2
        assert 0 <= slot1 < DEFAULT_SLOT_COUNT

    def test_key_to_slot_distribution(self):
        slots = {ShardRouter.key_to_slot(f"key-{i}") for i in range(10000)}
        assert len(slots) > 100
        for s in slots:
            assert 0 <= s < DEFAULT_SLOT_COUNT

    def test_key_to_slot_hash_tag(self):
        slot1 = ShardRouter.key_to_slot("user:{1001}:profile")
        slot2 = ShardRouter.key_to_slot("user:{1001}:orders")
        assert slot1 == slot2

    def test_key_to_slot_different_hash_tags(self):
        slot1 = ShardRouter.key_to_slot("user:{1001}")
        slot2 = ShardRouter.key_to_slot("user:{1002}")
        assert slot1 != slot2


class TestNodeManagement:
    def test_add_node(self):
        router = ShardRouter()
        router.add_node("node-a")
        nodes = router.list_nodes()
        assert len(nodes) == 1
        assert nodes[0].node_id == "node-a"

    def test_add_duplicate_node_noop(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.add_node("node-a")
        assert len(router.list_nodes()) == 1

    def test_add_empty_node_id_raises(self):
        router = ShardRouter()
        with pytest.raises(ValueError, match="node_id must not be empty"):
            router.add_node("")

    def test_remove_node(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.remove_node("node-a")
        assert len(router.list_nodes()) == 0

    def test_remove_nonexistent_node_raises(self):
        router = ShardRouter()
        with pytest.raises(NodeNotFoundError, match="node 'ghost' not found"):
            router.remove_node("ghost")

    def test_remove_node_with_slots_raises(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 0, 100)
        with pytest.raises(NodeNotEmptyError, match="still has assigned slots"):
            router.remove_node("node-a")

    def test_remove_node_with_ongoing_migration_raises(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)
        router.start_migration(50, "target")
        with pytest.raises(NodeNotEmptyError, match="still has assigned slots"):
            router.remove_node("source")
        with pytest.raises(NodeHasMigrationsError, match="has ongoing migrations"):
            router.remove_node("target")


class TestSlotAssignment:
    def test_assign_single_slot_range(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 0, 99)
        assert router.get_slot_owner(0) == "node-a"
        assert router.get_slot_owner(50) == "node-a"
        assert router.get_slot_owner(99) == "node-a"

    def test_assign_multiple_ranges(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.add_node("node-b")
        router.assign_slot_range("node-a", 0, 99)
        router.assign_slot_range("node-b", 100, 199)
        assert router.get_slot_owner(50) == "node-a"
        assert router.get_slot_owner(150) == "node-b"

    def test_assign_nonexistent_node_raises(self):
        router = ShardRouter()
        with pytest.raises(NodeNotFoundError):
            router.assign_slot_range("ghost", 0, 10)

    def test_assign_invalid_slot_range(self):
        router = ShardRouter()
        router.add_node("node-a")
        with pytest.raises(SlotRangeInvalidError):
            router.assign_slot_range("node-a", -1, 10)
        with pytest.raises(SlotRangeInvalidError):
            router.assign_slot_range("node-a", 0, 99999)
        with pytest.raises(SlotRangeInvalidError):
            router.assign_slot_range("node-a", 10, 5)

    def test_assign_overlapping_slots_raises(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.add_node("node-b")
        router.assign_slot_range("node-a", 0, 100)
        with pytest.raises(SlotAlreadyAssignedError):
            router.assign_slot_range("node-b", 50, 150)

    def test_unassign_slot_range(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 0, 99)
        router.unassign_slot_range(50, 60)
        assert router.get_slot_owner(0) == "node-a"
        assert router.get_slot_owner(50) is None
        assert router.get_slot_owner(60) is None
        assert router.get_slot_owner(61) == "node-a"

    def test_unassign_not_assigned_is_noop(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.unassign_slot_range(0, 100)
        assert router.get_slot_owner(50) is None


class TestBasicRouting:
    def test_route_basic(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.add_node("node-b")
        router.assign_slot_range("node-a", 0, 8191)
        router.assign_slot_range("node-b", 8192, 16383)
        for i in range(500):
            key = f"test-{i}"
            result = router.get_route(key)
            assert result.node_id in ("node-a", "node-b")
            assert 0 <= result.slot < 16384
            assert not result.migrating
            assert result.migration_target is None

    def test_route_unassigned_slot_raises(self):
        router = ShardRouter()
        router.add_node("node-a")
        with pytest.raises(SlotNotAssignedError):
            router.get_route("some-key")

    def test_route_consistency(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 0, 16383)
        for i in range(100):
            key = f"consistent-{i}"
            r1 = router.get_route(key)
            r2 = router.get_route(key)
            assert r1.node_id == r2.node_id
            assert r1.slot == r2.slot


class TestBoundaryConditions:
    def test_empty_router(self):
        router = ShardRouter()
        snap = router.get_snapshot()
        assert snap.total_slots == DEFAULT_SLOT_COUNT
        assert snap.assigned_slots == 0
        assert snap.unassigned_slots == DEFAULT_SLOT_COUNT
        assert snap.nodes == []

    def test_all_slots_single_node(self):
        router = ShardRouter()
        router.add_node("only-node")
        router.assign_slot_range("only-node", 0, DEFAULT_SLOT_COUNT - 1)
        snap = router.get_snapshot()
        assert snap.assigned_slots == DEFAULT_SLOT_COUNT
        assert snap.unassigned_slots == 0
        for i in range(100):
            result = router.get_route(f"k-{i}")
            assert result.node_id == "only-node"

    def test_no_slots_assigned(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.add_node("node-b")
        with pytest.raises(SlotNotAssignedError):
            router.get_route("any-key")

    def test_single_slot_assignment(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 5000, 5000)
        assert router.get_slot_owner(5000) == "node-a"
        assert router.get_slot_owner(4999) is None
        assert router.get_slot_owner(5001) is None


class TestMigrationDualWrite:
    def test_start_migration(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)
        router.start_migration(50, "target")
        migrating = router.get_migrating_slots()
        assert len(migrating) == 1
        assert migrating[0].slot == 50
        assert migrating[0].source_node_id == "source"
        assert migrating[0].target_node_id == "target"
        assert migrating[0].in_progress

    def test_dual_write_during_migration(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)

        slot = 50
        router.start_migration(slot, "target")

        key_in_slot = find_key_for_slot(slot)

        write_result = router.prepare_write(key_in_slot)
        assert write_result.status == WriteStatus.DUAL
        assert write_result.primary_node_id == "source"
        assert write_result.secondary_node_id == "target"
        assert write_result.slot == slot

    def test_route_during_migration(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)

        slot = 50
        router.start_migration(slot, "target")

        key_in_slot = find_key_for_slot(slot)

        route = router.get_route(key_in_slot)
        assert route.migrating is True
        assert route.node_id == "source"
        assert route.migration_target == "target"

    def test_complete_migration(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)
        router.start_migration(50, "target")
        router.complete_migration(50)
        assert router.get_slot_owner(50) == "target"
        assert len(router.get_migrating_slots()) == 0

    def test_route_after_migration(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)

        slot = 50
        router.start_migration(slot, "target")
        router.complete_migration(slot)

        key_in_slot = find_key_for_slot(slot)

        route = router.get_route(key_in_slot)
        assert route.node_id == "target"
        assert route.migrating is False
        assert route.migration_target is None

        write_result = router.prepare_write(key_in_slot)
        assert write_result.status == WriteStatus.SINGLE
        assert write_result.primary_node_id == "target"
        assert write_result.secondary_node_id is None

    def test_start_migration_unassigned_slot_raises(self):
        router = ShardRouter()
        router.add_node("target")
        with pytest.raises(SlotNotAssignedError):
            router.start_migration(0, "target")

    def test_start_migration_already_migrating_raises(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.add_node("other")
        router.assign_slot_range("source", 0, 100)
        router.start_migration(50, "target")
        with pytest.raises(SlotMigrationInProgressError):
            router.start_migration(50, "other")

    def test_complete_migration_not_migrating_raises(self):
        router = ShardRouter()
        with pytest.raises(SlotNotMigratingError):
            router.complete_migration(0)

    def test_start_migration_same_source_target_raises(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 0, 100)
        with pytest.raises(ValueError, match="source and target node must be different"):
            router.start_migration(50, "node-a")

    def test_assign_while_migrating_raises(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)
        router.start_migration(50, "target")
        with pytest.raises(SlotMigrationInProgressError):
            router.assign_slot_range("target", 50, 50)

    def test_unassign_while_migrating_raises(self):
        router = ShardRouter()
        router.add_node("source")
        router.add_node("target")
        router.assign_slot_range("source", 0, 100)
        router.start_migration(50, "target")
        with pytest.raises(SlotMigrationInProgressError):
            router.unassign_slot_range(50, 50)


class TestRedirectAfterMigration:
    def test_redirect_from_old_node(self):
        router = ShardRouter()
        router.add_node("old-node")
        router.add_node("new-node")
        router.assign_slot_range("old-node", 0, 100)

        slot = 50
        router.start_migration(slot, "new-node")
        router.complete_migration(slot)

        key_in_slot = find_key_for_slot(slot)

        with pytest.raises(RedirectRequiredError) as exc_info:
            router.route_from_node(key_in_slot, "old-node")
        assert exc_info.value.slot == slot
        assert exc_info.value.target_node_id == "new-node"

    def test_no_redirect_from_correct_node(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.add_node("node-b")
        router.assign_slot_range("node-a", 0, 8191)
        router.assign_slot_range("node-b", 8192, 16383)
        result = router.get_route("some-key")
        routed = router.route_from_node("some-key", result.node_id)
        assert routed.node_id == result.node_id

    def test_route_from_node_unassigned_slot_raises_slot_not_routed(self):
        router = ShardRouter()
        router.add_node("node-a")
        with pytest.raises(SlotNotRoutedError):
            router.route_from_node("any-key", "node-a")

    def test_route_from_node_unassigned_slot_is_not_slot_not_assigned(self):
        router = ShardRouter()
        router.add_node("node-a")
        with pytest.raises(SlotNotRoutedError):
            router.route_from_node("any-key", "node-a")
        with pytest.raises(SlotNotAssignedError):
            router.get_route("any-key")

    def test_slot_not_routed_distinct_from_redirect(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.add_node("node-b")
        with pytest.raises(SlotNotRoutedError):
            router.route_from_node("unassigned-key", "node-a")
        router.assign_slot_range("node-b", 0, 16383)
        result = router.get_route("any-key")
        with pytest.raises(RedirectRequiredError):
            router.route_from_node("any-key", "node-a")


class TestRoutingQueries:
    def test_get_node_slots_contiguous(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 100, 199)
        ranges = router.get_node_slots("node-a")
        assert len(ranges) == 1
        assert ranges[0].start == 100
        assert ranges[0].end == 199

    def test_get_node_slots_non_contiguous(self):
        router = ShardRouter()
        router.add_node("node-a")
        router.assign_slot_range("node-a", 0, 99)
        router.assign_slot_range("node-a", 200, 299)
        ranges = router.get_node_slots("node-a")
        assert len(ranges) == 2
        assert ranges[0].start == 0 and ranges[0].end == 99
        assert ranges[1].start == 200 and ranges[1].end == 299

    def test_get_node_slots_empty(self):
        router = ShardRouter()
        router.add_node("node-a")
        assert router.get_node_slots("node-a") == []

    def test_get_node_slots_nonexistent_raises(self):
        router = ShardRouter()
        with pytest.raises(NodeNotFoundError):
            router.get_node_slots("ghost")

    def test_get_all_assignments(self):
        router = ShardRouter()
        router.add_node("a")
        router.add_node("b")
        router.assign_slot_range("a", 0, 49)
        router.assign_slot_range("b", 50, 99)
        assignments = router.get_all_assignments()
        assert "a" in assignments
        assert "b" in assignments
        assert assignments["a"].total_slots == 50
        assert assignments["b"].total_slots == 50

    def test_get_migration_progress_empty(self):
        router = ShardRouter()
        progress = router.get_migration_progress()
        assert progress.total_migrating == 0
        assert progress.completed_migrations == 0
        assert progress.in_progress_slots == []

    def test_get_migration_progress_during_and_after(self):
        router = ShardRouter()
        router.add_node("s")
        router.add_node("t")
        router.assign_slot_range("s", 0, 100)
        router.start_migration(10, "t")
        router.start_migration(20, "t")
        router.complete_migration(10)
        progress = router.get_migration_progress()
        assert progress.total_migrating == 2
        assert progress.completed_migrations == 1
        assert len(progress.in_progress_slots) == 1
        assert progress.in_progress_slots[0].slot == 20

    def test_get_slot_owner_invalid(self):
        router = ShardRouter()
        with pytest.raises(SlotRangeInvalidError):
            router.get_slot_owner(-1)
        with pytest.raises(SlotRangeInvalidError):
            router.get_slot_owner(DEFAULT_SLOT_COUNT)

    def test_get_snapshot(self):
        router = ShardRouter()
        router.add_node("a")
        router.add_node("b")
        router.assign_slot_range("a", 0, 8191)
        snap = router.get_snapshot()
        assert isinstance(snap, RouterSnapshot)
        assert snap.total_slots == DEFAULT_SLOT_COUNT
        assert snap.assigned_slots == 8192
        assert snap.unassigned_slots == 8192
        assert len(snap.nodes) == 2
        assert isinstance(snap.migrations, MigrationProgress)


class TestWriteResult:
    def test_write_result_single(self):
        w = WriteResult(status=WriteStatus.SINGLE, primary_node_id="n1", slot=5)
        assert w.status == WriteStatus.SINGLE
        assert w.primary_node_id == "n1"
        assert w.secondary_node_id is None

    def test_write_result_dual(self):
        w = WriteResult(
            status=WriteStatus.DUAL,
            primary_node_id="n1",
            secondary_node_id="n2",
            slot=10,
        )
        assert w.status == WriteStatus.DUAL
        assert w.primary_node_id == "n1"
        assert w.secondary_node_id == "n2"


class TestModels:
    def test_shard_node(self):
        node = ShardNode(node_id="test", host="127.0.0.1", port=6379)
        assert node.node_id == "test"
        assert node.host == "127.0.0.1"
        assert node.port == 6379

    def test_slot_assignment_total_slots(self):
        sa = SlotAssignment(
            node_id="n",
            slot_ranges=[SlotRange(0, 9), SlotRange(20, 29)],
        )
        assert sa.total_slots == 20

    def test_route_result_defaults(self):
        rr = RouteResult(node_id="n1", slot=42)
        assert rr.migrating is False
        assert rr.migration_target is None


class TestCustomSlotCount:
    def test_small_slot_count(self):
        router = ShardRouter(total_slots=256)
        assert router.total_slots == 256
        router.add_node("node-a")
        router.assign_slot_range("node-a", 0, 255)
        for i in range(100):
            slot = ShardRouter.key_to_slot(f"k-{i}", 256)
            assert 0 <= slot < 256
            assert router.get_slot_owner(slot) == "node-a"

    def test_invalid_total_slots(self):
        with pytest.raises(ValueError, match="total_slots must be positive"):
            ShardRouter(total_slots=0)
        with pytest.raises(ValueError):
            ShardRouter(total_slots=-1)
