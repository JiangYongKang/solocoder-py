from __future__ import annotations

import pytest

from solocoder_py.anti_entropy import Replica, VersionError, VersionedEntry


class TestReplicaBasicOperations:
    def test_create_replica(self):
        replica = Replica(replica_id="node1")
        assert replica.replica_id == "node1"
        assert len(replica) == 0

    def test_put_and_get(self):
        replica = Replica(replica_id="node1")
        entry = replica.put("key1", "value1")
        assert entry.key == "key1"
        assert entry.value == "value1"
        assert entry.version == 1

        retrieved = replica.get("key1")
        assert retrieved is not None
        assert retrieved.value == "value1"
        assert retrieved.version == 1

    def test_put_with_explicit_version(self):
        replica = Replica(replica_id="node1")
        entry = replica.put("key1", "value1", version=5)
        assert entry.version == 5

    def test_put_updates_version(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        entry = replica.put("key1", "value2")
        assert entry.version == 2

    def test_put_with_higher_version(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1", version=1)
        entry = replica.put("key1", "value2", version=5)
        assert entry.version == 5

    def test_get_nonexistent_key(self):
        replica = Replica(replica_id="node1")
        assert replica.get("nonexistent") is None

    def test_delete(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        assert replica.delete("key1") is True
        assert replica.get("key1") is None
        assert len(replica) == 0

    def test_delete_nonexistent(self):
        replica = Replica(replica_id="node1")
        assert replica.delete("nonexistent") is False

    def test_has_key(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        assert replica.has_key("key1") is True
        assert replica.has_key("key2") is False

    def test_contains_operator(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        assert "key1" in replica
        assert "key2" not in replica

    def test_len(self):
        replica = Replica(replica_id="node1")
        assert len(replica) == 0
        replica.put("key1", "value1")
        assert len(replica) == 1
        replica.put("key2", "value2")
        assert len(replica) == 2

    def test_keys(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        replica.put("key2", "value2")
        keys = replica.keys()
        assert set(keys) == {"key1", "key2"}

    def test_entries(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        replica.put("key2", "value2")
        entries = replica.entries()
        assert len(entries) == 2
        keys = {e.key for e in entries}
        assert keys == {"key1", "key2"}

    def test_clear(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        replica.put("key2", "value2")
        replica.clear()
        assert len(replica) == 0

    def test_iter(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        replica.put("key2", "value2")
        keys = set(iter(replica))
        assert keys == {"key1", "key2"}


class TestReplicaVersionValidation:
    def test_negative_version_raises(self):
        replica = Replica(replica_id="node1")
        with pytest.raises(VersionError, match="version must be non-negative"):
            replica.put("key1", "value1", version=-1)

    def test_downgrade_version_raises(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1", version=5)
        with pytest.raises(VersionError, match="Cannot downgrade version"):
            replica.put("key1", "value2", version=3)

    def test_zero_version_allowed(self):
        replica = Replica(replica_id="node1")
        entry = replica.put("key1", "value1", version=0)
        assert entry.version == 0


class TestReplicaMergeEntry:
    def test_merge_new_entry(self):
        replica = Replica(replica_id="node1")
        entry = VersionedEntry(key="key1", value="value1", version=1)
        assert replica.merge_entry(entry) is True
        assert replica.get("key1").value == "value1"
        assert replica.get("key1").version == 1

    def test_merge_higher_version(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "old_value", version=1)
        entry = VersionedEntry(key="key1", value="new_value", version=2)
        assert replica.merge_entry(entry) is True
        assert replica.get("key1").value == "new_value"
        assert replica.get("key1").version == 2

    def test_merge_lower_version_noop(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1", version=3)
        entry = VersionedEntry(key="key1", value="value2", version=2)
        assert replica.merge_entry(entry) is False
        assert replica.get("key1").value == "value1"
        assert replica.get("key1").version == 3

    def test_merge_same_version_same_value_noop(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1", version=2)
        entry = VersionedEntry(key="key1", value="value1", version=2)
        assert replica.merge_entry(entry) is False

    def test_merge_same_version_different_value_noop(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "old_value", version=2)
        entry = VersionedEntry(key="key1", value="new_value", version=2)
        assert replica.merge_entry(entry) is False
        assert replica.get("key1").value == "old_value"
        assert replica.get("key1").version == 2


class TestReplicaForceMergeEntry:
    def test_force_merge_new_entry(self):
        replica = Replica(replica_id="node1")
        entry = VersionedEntry(key="key1", value="value1", version=1)
        assert replica.force_merge_entry(entry) is True
        assert replica.get("key1").value == "value1"
        assert replica.get("key1").version == 1

    def test_force_merge_higher_version(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "old_value", version=1)
        entry = VersionedEntry(key="key1", value="new_value", version=3)
        assert replica.force_merge_entry(entry) is True
        assert replica.get("key1").value == "new_value"
        assert replica.get("key1").version == 3

    def test_force_merge_lower_version_overwrites(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1", version=3)
        entry = VersionedEntry(key="key1", value="value2", version=1)
        assert replica.force_merge_entry(entry) is True
        assert replica.get("key1").value == "value2"
        assert replica.get("key1").version == 1

    def test_force_merge_same_version_different_value_overwrites(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "old_value", version=2)
        entry = VersionedEntry(key="key1", value="new_value", version=2)
        assert replica.force_merge_entry(entry) is True
        assert replica.get("key1").value == "new_value"
        assert replica.get("key1").version == 2

    def test_force_merge_same_version_same_value_overwrites(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1", version=2)
        entry = VersionedEntry(key="key1", value="value1", version=2)
        assert replica.force_merge_entry(entry) is True


class TestReplicaIdValidation:
    def test_none_replica_id_raises(self):
        with pytest.raises(ValueError, match="replica_id cannot be None"):
            Replica(replica_id=None)

    def test_empty_replica_id_allowed(self):
        replica = Replica(replica_id="")
        assert replica.replica_id == ""

    def test_non_string_replica_id_raises(self):
        with pytest.raises(TypeError, match="replica_id must be a string"):
            Replica(replica_id=123)


class TestReplicaToDict:
    def test_to_dict_returns_copy(self):
        replica = Replica(replica_id="node1")
        replica.put("key1", "value1")
        data = replica.to_dict()
        assert "key1" in data
        assert data["key1"].value == "value1"

        data["key1"].value = "modified"
        assert replica.get("key1").value == "value1"

    def test_to_dict_empty(self):
        replica = Replica(replica_id="node1")
        data = replica.to_dict()
        assert len(data) == 0
