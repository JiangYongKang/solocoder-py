from __future__ import annotations

import pytest

from solocoder_py.anti_entropy import AntiEntropyEngine, EntryStatus, Replica


class TestDiffIdenticalReplicas:
    def test_both_empty(self, engine):
        diff = engine.diff()
        assert not diff.has_differences
        assert len(diff.only_in_a) == 0
        assert len(diff.only_in_b) == 0
        assert len(diff.a_has_newer) == 0
        assert len(diff.b_has_newer) == 0
        assert len(diff.conflicts) == 0
        assert len(diff.identical) == 0
        assert diff.diff_count == 0
        assert diff.version_mismatch_count == 0

    def test_identical_entries(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value1", version=1)
        replica_a.put("key2", "value2", version=2)
        replica_b.put("key1", "value1", version=1)
        replica_b.put("key2", "value2", version=2)

        diff = engine.diff()
        assert not diff.has_differences
        assert "key1" in diff.identical
        assert "key2" in diff.identical
        assert diff.diff_count == 0
        assert diff.version_mismatch_count == 0


class TestDiffOnlyInOneSide:
    def test_only_in_a(self, replica_a, engine):
        replica_a.put("key1", "value1", version=1)
        replica_a.put("key2", "value2", version=1)

        diff = engine.diff()
        assert diff.has_differences
        assert len(diff.only_in_a) == 2
        assert "key1" in diff.only_in_a
        assert "key2" in diff.only_in_a
        assert diff.only_in_a["key1"].value == "value1"
        assert diff.only_in_a["key2"].value == "value2"
        assert len(diff.only_in_b) == 0
        assert diff.diff_count == 2

    def test_only_in_b(self, replica_b, engine):
        replica_b.put("key1", "value1", version=1)
        replica_b.put("key2", "value2", version=1)

        diff = engine.diff()
        assert diff.has_differences
        assert len(diff.only_in_b) == 2
        assert "key1" in diff.only_in_b
        assert "key2" in diff.only_in_b
        assert len(diff.only_in_a) == 0
        assert diff.diff_count == 2


class TestDiffVersionMismatch:
    def test_a_has_higher_version(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value_v2", version=2)
        replica_b.put("key1", "value_v1", version=1)

        diff = engine.diff()
        assert diff.has_differences
        assert len(diff.a_has_newer) == 1
        assert len(diff.b_has_newer) == 0
        assert "key1" in diff.a_has_newer
        entry = diff.a_has_newer["key1"]
        assert entry.status == EntryStatus.A_HAS_NEWER
        assert entry.entry_a.version == 2
        assert entry.entry_b.version == 1
        assert entry.newer_entry.version == 2
        assert entry.older_entry.version == 1
        assert diff.diff_count == 1
        assert diff.version_mismatch_count == 1

    def test_b_has_higher_version(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value_v1", version=1)
        replica_b.put("key1", "value_v2", version=3)

        diff = engine.diff()
        assert diff.has_differences
        assert len(diff.a_has_newer) == 0
        assert len(diff.b_has_newer) == 1
        assert "key1" in diff.b_has_newer
        entry = diff.b_has_newer["key1"]
        assert entry.status == EntryStatus.B_HAS_NEWER
        assert entry.entry_a.version == 1
        assert entry.entry_b.version == 3
        assert entry.newer_entry.version == 3
        assert entry.older_entry.version == 1
        assert diff.diff_count == 1
        assert diff.version_mismatch_count == 1

    def test_same_version_same_value_identical(self, replica_a, replica_b, engine):
        replica_a.put("key1", "same_value", version=5)
        replica_b.put("key1", "same_value", version=5)

        diff = engine.diff()
        assert not diff.has_differences
        assert "key1" in diff.identical
        assert len(diff.a_has_newer) == 0
        assert len(diff.b_has_newer) == 0
        assert len(diff.conflicts) == 0

    def test_multiple_mixed_mismatches(self, replica_a, replica_b, engine):
        replica_a.put("k1", "a_high", version=3)
        replica_a.put("k2", "a_low", version=1)
        replica_a.put("k3", "same", version=2)
        replica_b.put("k1", "b_low", version=1)
        replica_b.put("k2", "b_high", version=4)
        replica_b.put("k3", "same", version=2)

        diff = engine.diff()
        assert len(diff.a_has_newer) == 1
        assert "k1" in diff.a_has_newer
        assert len(diff.b_has_newer) == 1
        assert "k2" in diff.b_has_newer
        assert "k3" in diff.identical
        assert diff.version_mismatch_count == 2


class TestDiffConflicts:
    def test_same_version_different_value(self, replica_a, replica_b, engine):
        replica_a.put("key1", "value_a", version=2)
        replica_b.put("key1", "value_b", version=2)

        diff = engine.diff()
        assert diff.has_differences
        assert diff.has_conflicts
        assert len(diff.conflicts) == 1
        assert "key1" in diff.conflicts
        conflict = diff.conflicts["key1"]
        assert conflict.status == EntryStatus.CONFLICT
        assert conflict.entry_a.value == "value_a"
        assert conflict.entry_b.value == "value_b"
        assert conflict.entry_a.version == conflict.entry_b.version == 2
        assert diff.diff_count == 1

    def test_multiple_conflicts(self, replica_a, replica_b, engine):
        replica_a.put("key1", "a_val1", version=1)
        replica_a.put("key2", "a_val2", version=2)
        replica_b.put("key1", "b_val1", version=1)
        replica_b.put("key2", "b_val2", version=2)

        diff = engine.diff()
        assert diff.has_conflicts
        assert len(diff.conflicts) == 2
        assert "key1" in diff.conflicts
        assert "key2" in diff.conflicts


class TestDiffMixedScenarios:
    def test_mixed_differences(self, replica_a, replica_b, engine):
        replica_a.put("only_a", "val_a", version=1)
        replica_a.put("shared_high", "val_v3", version=3)
        replica_a.put("identical", "same", version=2)
        replica_a.put("conflict_key", "a_val", version=1)

        replica_b.put("only_b", "val_b", version=1)
        replica_b.put("shared_high", "val_v1", version=1)
        replica_b.put("identical", "same", version=2)
        replica_b.put("conflict_key", "b_val", version=1)

        diff = engine.diff()
        assert diff.has_differences
        assert len(diff.only_in_a) == 1
        assert "only_a" in diff.only_in_a
        assert len(diff.only_in_b) == 1
        assert "only_b" in diff.only_in_b
        assert len(diff.a_has_newer) == 1
        assert "shared_high" in diff.a_has_newer
        assert len(diff.conflicts) == 1
        assert "conflict_key" in diff.conflicts
        assert "identical" in diff.identical
        assert diff.diff_count == 4
        assert diff.version_mismatch_count == 1

    def test_all_keys_present_but_various_states(self, replica_a, replica_b, engine):
        for i in range(10):
            replica_a.put(f"key_{i}", f"a_val_{i}", version=i + 1)
            replica_b.put(f"key_{i}", f"b_val_{i}", version=i + 1)

        diff = engine.diff()
        assert len(diff.conflicts) == 10
        assert diff.has_conflicts


class TestDiffEntryHelpers:
    def test_newer_entry_a_has_newer(self, replica_a, replica_b, engine):
        replica_a.put("k", "v2", version=2)
        replica_b.put("k", "v1", version=1)
        diff = engine.diff()
        entry = diff.a_has_newer["k"]
        assert entry.newer_entry is entry.entry_a
        assert entry.older_entry is entry.entry_b

    def test_newer_entry_b_has_newer(self, replica_a, replica_b, engine):
        replica_a.put("k", "v1", version=1)
        replica_b.put("k", "v2", version=2)
        diff = engine.diff()
        entry = diff.b_has_newer["k"]
        assert entry.newer_entry is entry.entry_b
        assert entry.older_entry is entry.entry_a

    def test_newer_entry_conflict_returns_none(self, replica_a, replica_b, engine):
        replica_a.put("k", "va", version=2)
        replica_b.put("k", "vb", version=2)
        diff = engine.diff()
        entry = diff.conflicts["k"]
        assert entry.newer_entry is None
        assert entry.older_entry is None
