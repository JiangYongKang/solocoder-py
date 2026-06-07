from __future__ import annotations

import pytest

from solocoder_py.consistent_hash import (
    ConsistentHashRing,
    EmptyRingError,
    InvalidVirtualNodesError,
    InvalidWeightError,
    NodeAlreadyExistsError,
    NodeNotFoundError,
)


class TestRingBasicOperations:
    def test_add_single_node(self):
        ring = ConsistentHashRing(default_virtual_nodes=50)
        ring.add_node("node-a")
        assert ring.node_count == 1
        assert ring.total_virtual_nodes == 50

    def test_add_multiple_nodes(self):
        ring = ConsistentHashRing(default_virtual_nodes=30)
        ring.add_node("node-a")
        ring.add_node("node-b")
        ring.add_node("node-c")
        assert ring.node_count == 3
        assert ring.total_virtual_nodes == 90

    def test_add_node_with_explicit_virtual_nodes(self):
        ring = ConsistentHashRing(default_virtual_nodes=50)
        ring.add_node("node-a", virtual_nodes=200)
        assert ring.total_virtual_nodes == 200

    def test_remove_node(self):
        ring = ConsistentHashRing(default_virtual_nodes=50)
        ring.add_node("node-a")
        ring.add_node("node-b")
        ring.remove_node("node-a")
        assert ring.node_count == 1
        assert ring.total_virtual_nodes == 50
        nodes = ring.get_nodes()
        assert [n.node_id for n in nodes] == ["node-b"]

    def test_remove_all_nodes(self):
        ring = ConsistentHashRing(default_virtual_nodes=10)
        ring.add_node("a")
        ring.add_node("b")
        ring.remove_node("a")
        ring.remove_node("b")
        assert ring.node_count == 0
        assert ring.total_virtual_nodes == 0


class TestKeyRouting:
    def test_route_returns_existing_node(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("node-a")
        ring.add_node("node-b")
        ring.add_node("node-c")
        nodes = {"node-a", "node-b", "node-c"}
        for i in range(100):
            result = ring.get_node(f"key-{i}")
            assert result in nodes

    def test_route_consistency(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("x")
        ring.add_node("y")
        ring.add_node("z")
        for i in range(50):
            k = f"consistent-key-{i}"
            a = ring.get_node(k)
            b = ring.get_node(k)
            assert a == b

    def test_single_node_routes_all_keys(self):
        ring = ConsistentHashRing(default_virtual_nodes=50)
        ring.add_node("only-node")
        for i in range(200):
            assert ring.get_node(f"k{i}") == "only-node"


class TestEmptyRing:
    def test_get_node_on_empty_ring_raises(self):
        ring = ConsistentHashRing()
        with pytest.raises(EmptyRingError, match="hash ring is empty"):
            ring.get_node("some-key")

    def test_initial_empty(self):
        ring = ConsistentHashRing()
        assert ring.node_count == 0
        assert ring.total_virtual_nodes == 0
        assert ring.get_nodes() == []


class TestDuplicateAndMissingNodes:
    def test_add_duplicate_node_raises(self):
        ring = ConsistentHashRing()
        ring.add_node("node-a")
        with pytest.raises(NodeAlreadyExistsError, match="node 'node-a' already exists"):
            ring.add_node("node-a")

    def test_remove_nonexistent_node_raises(self):
        ring = ConsistentHashRing()
        ring.add_node("node-a")
        with pytest.raises(NodeNotFoundError, match="node 'node-b' not found"):
            ring.remove_node("node-b")

    def test_get_node_info_nonexistent_raises(self):
        ring = ConsistentHashRing()
        with pytest.raises(NodeNotFoundError, match="node 'ghost' not found"):
            ring.get_node_info("ghost")


class TestInvalidParameters:
    def test_invalid_default_virtual_nodes(self):
        with pytest.raises(InvalidVirtualNodesError):
            ConsistentHashRing(default_virtual_nodes=0)
        with pytest.raises(InvalidVirtualNodesError):
            ConsistentHashRing(default_virtual_nodes=-5)

    def test_invalid_virtual_nodes_on_add(self):
        ring = ConsistentHashRing()
        with pytest.raises(InvalidVirtualNodesError):
            ring.add_node("a", virtual_nodes=0)
        with pytest.raises(InvalidVirtualNodesError):
            ring.add_node("a", virtual_nodes=-10)

    def test_invalid_weight(self):
        ring = ConsistentHashRing()
        with pytest.raises(InvalidWeightError, match="weight must be positive"):
            ring.add_node("a", weight=0)
        with pytest.raises(InvalidWeightError):
            ring.add_node("a", weight=-1.5)

    def test_empty_node_id(self):
        ring = ConsistentHashRing()
        with pytest.raises(ValueError, match="node_id must not be empty"):
            ring.add_node("")


class TestWeightAndVirtualNodes:
    def test_weight_increases_virtual_nodes(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("light", weight=1.0)
        ring.add_node("heavy", weight=3.0)
        light_info = ring.get_node_info("light")
        heavy_info = ring.get_node_info("heavy")
        assert heavy_info.virtual_nodes >= light_info.virtual_nodes * 2

    def test_high_weight_node_gets_more_hits(self):
        ring = ConsistentHashRing(default_virtual_nodes=200)
        ring.add_node("low", weight=1.0)
        ring.add_node("high", weight=4.0)

        hits = {"low": 0, "high": 0}
        for i in range(20000):
            node = ring.get_node(f"sample-{i}")
            hits[node] += 1

        assert hits["high"] > hits["low"]
        ratio = hits["high"] / (hits["high"] + hits["low"])
        assert 0.65 < ratio < 0.95

    def test_explicit_virtual_nodes_overrides_weight(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("a", virtual_nodes=500, weight=0.1)
        info = ring.get_node_info("a")
        assert info.virtual_nodes == 500


class TestMigrationStats:
    def test_adding_node_migrates_small_ratio(self):
        ring = ConsistentHashRing(default_virtual_nodes=200)
        ring.add_node("a")
        ring.add_node("b")
        ring.add_node("c")

        keys = [f"k-{i}" for i in range(10000)]
        before = ring.get_snapshot()

        ring.add_node("d")
        stats = ring.get_migration_stats(keys, before=before)

        assert stats.total_keys == 10000
        assert 0 < stats.migrated_keys < 10000
        assert 0.15 < stats.migration_ratio < 0.40

    def test_removing_node_migrates_its_keys(self):
        ring = ConsistentHashRing(default_virtual_nodes=200)
        ring.add_node("a")
        ring.add_node("b")
        ring.add_node("c")

        keys = [f"k-{i}" for i in range(10000)]
        before = ring.get_snapshot()

        ring.remove_node("b")
        stats = ring.get_migration_stats(keys, before=before)

        assert stats.total_keys == 10000
        assert 0.20 < stats.migration_ratio < 0.50
        assert stats.migrated_from.get("b", 0) > 0

    def test_no_change_no_migration(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("a")
        ring.add_node("b")

        keys = [f"k-{i}" for i in range(5000)]
        snap = ring.get_snapshot()
        stats = ring.get_migration_stats(keys, before=snap, after=snap)

        assert stats.migrated_keys == 0
        assert stats.migration_ratio == 0.0

    def test_migration_from_and_to_counts(self):
        ring = ConsistentHashRing(default_virtual_nodes=200)
        ring.add_node("a")
        ring.add_node("b")
        keys = [f"k-{i}" for i in range(10000)]
        before = ring.get_snapshot()

        ring.add_node("c")
        stats = ring.get_migration_stats(keys, before=before)

        total_from = sum(stats.migrated_from.values())
        total_to = sum(stats.migrated_to.values())
        assert total_from == stats.migrated_keys
        assert total_to == stats.migrated_keys
        assert "c" in stats.migrated_to

    def test_empty_keys_stats(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("a")
        snap = ring.get_snapshot()
        ring.add_node("b")
        stats = ring.get_migration_stats([], before=snap)
        assert stats.total_keys == 0
        assert stats.migrated_keys == 0
        assert stats.migration_ratio == 0.0


class TestRingStateQuery:
    def test_get_nodes(self):
        ring = ConsistentHashRing(default_virtual_nodes=50)
        ring.add_node("a", weight=1.0)
        ring.add_node("b", weight=2.0)
        nodes = ring.get_nodes()
        ids = sorted(n.node_id for n in nodes)
        assert ids == ["a", "b"]

    def test_get_node_info(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("alpha", weight=2.5)
        info = ring.get_node_info("alpha")
        assert info.node_id == "alpha"
        assert info.weight == 2.5
        assert info.virtual_nodes > 0
        assert info.estimated_key_count > 0

    def test_get_snapshot(self):
        ring = ConsistentHashRing(default_virtual_nodes=30)
        ring.add_node("x")
        ring.add_node("y")
        snap = ring.get_snapshot()
        assert len(snap.nodes) == 2
        assert snap.total_virtual_nodes == 60
        assert len(snap.virtual_nodes) == 60
        for v in snap.virtual_nodes:
            assert v.physical_node_id in {"x", "y"}

    def test_estimated_key_count_proportional(self):
        ring = ConsistentHashRing(default_virtual_nodes=100)
        ring.add_node("small", weight=1)
        ring.add_node("big", weight=3)
        small_info = ring.get_node_info("small")
        big_info = ring.get_node_info("big")
        assert big_info.estimated_key_count >= small_info.estimated_key_count * 2


class TestNodeCountAndVirtualNodeCount:
    def test_node_count_reflects_add_remove(self):
        ring = ConsistentHashRing()
        assert ring.node_count == 0
        ring.add_node("a")
        assert ring.node_count == 1
        ring.add_node("b")
        assert ring.node_count == 2
        ring.remove_node("a")
        assert ring.node_count == 1
        ring.remove_node("b")
        assert ring.node_count == 0

    def test_total_virtual_nodes_sum(self):
        ring = ConsistentHashRing()
        ring.add_node("a", virtual_nodes=10)
        ring.add_node("b", virtual_nodes=20)
        ring.add_node("c", virtual_nodes=30)
        assert ring.total_virtual_nodes == 60
        ring.remove_node("b")
        assert ring.total_virtual_nodes == 40


class TestMigrationStatsErrors:
    def test_migration_stats_needs_snapshot(self):
        ring = ConsistentHashRing()
        with pytest.raises(ValueError, match="at least one of before or after must be provided"):
            ring.get_migration_stats([])


class TestRouteWraparound:
    def test_keys_hash_greater_than_max_vnode_wrap(self):
        ring = ConsistentHashRing(default_virtual_nodes=10)
        ring.add_node("wrap-node")
        max_hash = 2**32 - 1
        high_key = str(max_hash)
        result = ring.get_node(high_key)
        assert result == "wrap-node"
