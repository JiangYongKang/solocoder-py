from __future__ import annotations

import pytest

from solocoder_py.anti_entropy import AntiEntropyEngine, Replica


class TestSyncAToB:
    def test_a_has_new_entries(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=1)
        replica_a.put("key2", "value2", version=1)

        result = engine.sync_a_to_b()

        assert result.a_to_b_count == 2
        assert result.b_to_a_count == 0
        assert result.total_synced == 2
        assert "key1" in result.synced_keys
        assert "key2" in result.synced_keys
        assert replica_b.get("key1").value == "value1"
        assert replica_b.get("key2").value == "value2"
        assert replica_b.get("key1").version == 1
        assert engine.is_consistent()

    def test_a_has_higher_version(self, replica_a, replica_b, engine):
        replica_a.put("key1", "new_value", version=3)
        replica_b.put("key1", "old_value", version=1)

        result = engine.sync_a_to_b()

        assert result.a_to_b_count == 1
        assert replica_b.get("key1").value == "new_value"
        assert replica_b.get("key1").version == 3
        assert engine.is_consistent()

    def test_a_has_lower_version_no_change(self, replica_a, replica_b, engine):
        replica_a.put("key1", "old_value", version=1)
        replica_b.put("key1", "new_value", version=3)

        result = engine.sync_a_to_b()

        assert result.a_to_b_count == 0
        assert replica_b.get("key1").value == "new_value"
        assert replica_b.get("key1").version == 3
        assert not engine.is_consistent()

    def test_conflict_in_a_to_b(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value_a", version=2)
        replica_b.put("key1", "value_b", version=2)

        result = engine.sync_a_to_b()

        assert result.a_to_b_count == 0
        assert result.has_conflicts
        assert "key1" in result.conflict_keys
        assert replica_b.get("key1").value == "value_b"

        conflicts = engine.get_conflicts()
        assert "key1" in conflicts

    def test_identical_entries_noop(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=1)
        replica_b.put("key1", "value1", version=1)

        result = engine.sync_a_to_b()

        assert result.a_to_b_count == 0
        assert result.total_synced == 0
        assert engine.is_consistent()


class TestSyncBToA:
    def test_b_has_new_entries(self, replica_a, replica_b, engine):
        replica_b.put("key1", "value1", version=1)
        replica_b.put("key2", "value2", version=1)

        result = engine.sync_b_to_a()

        assert result.b_to_a_count == 2
        assert result.a_to_b_count == 0
        assert result.total_synced == 2
        assert replica_a.get("key1").value == "value1"
        assert replica_a.get("key2").value == "value2"
        assert engine.is_consistent()

    def test_b_has_higher_version(self, replica_a, replica_b, engine):
        replica_a.put("key1", "old_value", version=1)
        replica_b.put("key1", "new_value", version=3)

        result = engine.sync_b_to_a()

        assert result.b_to_a_count == 1
        assert replica_a.get("key1").value == "new_value"
        assert replica_a.get("key1").version == 3
        assert engine.is_consistent()

    def test_conflict_in_b_to_a(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value_a", version=2)
        replica_b.put("key1", "value_b", version=2)

        result = engine.sync_b_to_a()

        assert result.b_to_a_count == 0
        assert result.has_conflicts
        assert "key1" in result.conflict_keys
        assert replica_a.get("key1").value == "value_a"


class TestSyncBidirectional:
    def test_both_have_unique_entries(self, replica_a, replica_b, engine):
        replica_a.put("only_a", "val_a", version=1)
        replica_b.put("only_b", "val_b", version=1)

        result = engine.sync_bidirectional()

        assert result.a_to_b_count == 1
        assert result.b_to_a_count == 1
        assert result.total_synced == 2
        assert "only_a" in result.synced_keys
        assert "only_b" in result.synced_keys
        assert replica_a.get("only_b").value == "val_b"
        assert replica_b.get("only_a").value == "val_a"
        assert engine.is_consistent()

    def test_version_mismatch_high_wins(self, replica_a, replica_b, engine):
        replica_a.put("key1", "v2_a", version=2)
        replica_a.put("key2", "v1_a", version=1)
        replica_b.put("key1", "v1_b", version=1)
        replica_b.put("key2", "v3_b", version=3)

        result = engine.sync_bidirectional()

        assert result.total_synced == 2
        assert replica_a.get("key1").value == "v2_a"
        assert replica_a.get("key1").version == 2
        assert replica_b.get("key1").value == "v2_a"
        assert replica_b.get("key1").version == 2
        assert replica_a.get("key2").value == "v3_b"
        assert replica_a.get("key2").version == 3
        assert replica_b.get("key2").value == "v3_b"
        assert replica_b.get("key2").version == 3
        assert engine.is_consistent()

    def test_conflicts_preserved(self, replica_a, replica_b, engine):
        replica_a.put("key1", "val_a", version=2)
        replica_b.put("key1", "val_b", version=2)

        result = engine.sync_bidirectional()

        assert result.total_synced == 0
        assert result.has_conflicts
        assert "key1" in result.conflict_keys
        assert replica_a.get("key1").value == "val_a"
        assert replica_b.get("key1").value == "val_b"
        assert not engine.is_consistent()


class TestConflictResolution:
    def test_resolve_conflict_a_wins(self, replica_a, replica_b, engine):
        replica_a.put("key1", "val_a", version=2)
        replica_b.put("key1", "val_b", version=2)
        engine.sync_bidirectional()

        assert engine.resolve_conflict("key1", "a") is True

        assert replica_a.get("key1").value == "val_a"
        assert replica_b.get("key1").value == "val_a"
        assert engine.is_consistent()
        assert "key1" not in engine.get_conflicts()

    def test_resolve_conflict_b_wins(self, replica_a, replica_b, engine):
        replica_a.put("key1", "val_a", version=2)
        replica_b.put("key1", "val_b", version=2)
        engine.sync_bidirectional()

        assert engine.resolve_conflict("key1", "b") is True

        assert replica_a.get("key1").value == "val_b"
        assert replica_b.get("key1").value == "val_b"
        assert engine.is_consistent()

    def test_resolve_nonexistent_conflict(self, engine):
        assert engine.resolve_conflict("nonexistent", "a") is False

    def test_resolve_invalid_winner(self, replica_a, replica_b, engine):
        replica_a.put("key1", "val_a", version=2)
        replica_b.put("key1", "val_b", version=2)
        engine.sync_bidirectional()

        with pytest.raises(ValueError, match="winner must be 'a' or 'b'"):
            engine.resolve_conflict("key1", "invalid")

    def test_clear_conflicts(self, replica_a, replica_b, engine):
        replica_a.put("key1", "val_a", version=2)
        replica_b.put("key1", "val_b", version=2)
        engine.sync_bidirectional()

        assert len(engine.get_conflicts()) == 1
        engine.clear_conflicts()
        assert len(engine.get_conflicts()) == 0


class TestIsConsistent:
    def test_empty_replicas_consistent(self, engine):
        assert engine.is_consistent() is True

    def test_identical_replicas_consistent(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=1)
        replica_a.put("key2", "value2", version=2)
        replica_b.put("key1", "value1", version=1)
        replica_b.put("key2", "value2", version=2)

        assert engine.is_consistent() is True

    def test_different_replicas_not_consistent(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=1)
        assert engine.is_consistent() is False


class TestSyncEdgeCases:
    def test_sync_idempotent(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=2)
        replica_a.put("key2", "value2", version=3)
        replica_b.put("key1", "old_value", version=1)

        result1 = engine.sync_a_to_b()
        assert result1.a_to_b_count == 2

        result2 = engine.sync_a_to_b()
        assert result2.a_to_b_count == 0
        assert engine.is_consistent()

    def test_full_sync_then_noop(self, replica_a, replica_b, engine):
        replica_a.put("k1", "v1", version=1)
        replica_a.put("k2", "v2", version=2)
        replica_a.put("k3", "v3", version=3)

        result = engine.sync_bidirectional()
        assert result.total_synced == 3
        assert engine.is_consistent()

        result2 = engine.sync_bidirectional()
        assert result2.total_synced == 0
        assert engine.is_consistent()

    def test_multiple_rounds_converge(self, replica_a, replica_b, engine):
        replica_a.put("a_only", "val_a", version=1)
        replica_a.put("shared", "a_version", version=5)
        replica_b.put("b_only", "val_b", version=1)
        replica_b.put("shared", "b_version", version=3)

        result = engine.sync_bidirectional()
        assert result.total_synced == 3
        assert result.a_to_b_count == 2
        assert result.b_to_a_count == 1
        assert engine.is_consistent()
