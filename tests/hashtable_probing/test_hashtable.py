import pytest

from solocoder_py.hashtable_probing import KeyNotFoundError, ProbingHashTable


class _FixedHashKey:
    def __init__(self, key: str, fixed_hash: int):
        self._key = key
        self._fixed_hash = fixed_hash

    def __hash__(self):
        return self._fixed_hash

    def __eq__(self, other):
        if not isinstance(other, _FixedHashKey):
            return NotImplemented
        return self._key == other._key

    def __repr__(self):
        return f"FHK({self._key!r})"


class TestInsertFindDelete:
    def test_insert_and_find(self, ht: ProbingHashTable):
        ht.insert("a", 1)
        ht.insert("b", 2)
        ht.insert("c", 3)
        assert ht.find("a") == 1
        assert ht.find("b") == 2
        assert ht.find("c") == 3

    def test_insert_update_existing_key(self, ht: ProbingHashTable):
        ht.insert("x", 10)
        ht.insert("x", 20)
        assert ht.find("x") == 20
        assert ht.size() == 1

    def test_delete_key(self, ht: ProbingHashTable):
        ht.insert("a", 1)
        ht.insert("b", 2)
        value = ht.delete("a")
        assert value == 1
        assert ht.size() == 1
        assert ht.find("b") == 2
        with pytest.raises(KeyNotFoundError):
            ht.find("a")

    def test_delete_returns_value(self, ht: ProbingHashTable):
        ht.insert("k", "val")
        result = ht.delete("k")
        assert result == "val"

    def test_find_nonexistent_key(self, ht: ProbingHashTable):
        with pytest.raises(KeyNotFoundError):
            ht.find("missing")

    def test_delete_nonexistent_key(self, ht: ProbingHashTable):
        with pytest.raises(KeyNotFoundError):
            ht.delete("missing")

    def test_contains(self, ht: ProbingHashTable):
        ht.insert("a", 1)
        assert ht.contains("a") is True
        assert ht.contains("b") is False

    def test_in_operator(self, ht: ProbingHashTable):
        ht.insert("a", 1)
        assert "a" in ht
        assert "b" not in ht


class TestEmptyTableOperations:
    def test_find_on_empty(self, ht: ProbingHashTable):
        with pytest.raises(KeyNotFoundError):
            ht.find("any")

    def test_delete_on_empty(self, ht: ProbingHashTable):
        with pytest.raises(KeyNotFoundError):
            ht.delete("any")

    def test_contains_on_empty(self, ht: ProbingHashTable):
        assert ht.contains("any") is False

    def test_size_on_empty(self, ht: ProbingHashTable):
        assert ht.size() == 0
        assert ht.is_empty() is True
        assert len(ht) == 0

    def test_load_factor_on_empty(self, ht: ProbingHashTable):
        assert ht.load_factor() == 0.0


class TestLazyDeletion:
    def test_delete_then_insert_reuses_slot(self, ht: ProbingHashTable):
        k_a = _FixedHashKey("a", 0)
        k_b = _FixedHashKey("b", 1)
        k_c = _FixedHashKey("c", 0)
        ht.insert(k_a, 1)
        ht.insert(k_b, 2)
        ht.delete(k_a)
        assert ht.deleted_count() == 1
        ht.insert(k_c, 3)
        assert ht.deleted_count() == 0
        assert ht.size() == 2
        assert ht.find(k_b) == 2
        assert ht.find(k_c) == 3

    def test_find_skips_deleted_markers(self, ht: ProbingHashTable):
        k1 = _FixedHashKey("first", 0)
        k2 = _FixedHashKey("second", 0)
        k3 = _FixedHashKey("third", 0)
        ht.insert(k1, "v1")
        ht.insert(k2, "v2")
        ht.insert(k3, "v3")
        ht.delete(k2)
        assert ht.find(k3) == "v3"
        assert ht.find(k1) == "v1"

    def test_delete_skips_deleted_markers(self, ht: ProbingHashTable):
        k1 = _FixedHashKey("first", 0)
        k2 = _FixedHashKey("second", 0)
        k3 = _FixedHashKey("third", 0)
        ht.insert(k1, "v1")
        ht.insert(k2, "v2")
        ht.insert(k3, "v3")
        ht.delete(k2)
        result = ht.delete(k3)
        assert result == "v3"
        assert ht.find(k1) == "v1"

    def test_multiple_deletes_accumulate_markers(self, ht: ProbingHashTable):
        for i in range(5):
            ht.insert(i, i * 10)
        for i in range(4):
            ht.delete(i)
        assert ht.deleted_count() == 4
        assert ht.size() == 1
        assert ht.find(4) == 40


class TestLinearProbing:
    def test_two_keys_same_slot_insert_and_find(self, ht: ProbingHashTable):
        k1 = _FixedHashKey("alpha", 0)
        k2 = _FixedHashKey("beta", 0)
        ht.insert(k1, "v1")
        ht.insert(k2, "v2")
        assert ht.find(k1) == "v1"
        assert ht.find(k2) == "v2"

    def test_two_keys_same_slot_delete_first(self, ht: ProbingHashTable):
        k1 = _FixedHashKey("alpha", 0)
        k2 = _FixedHashKey("beta", 0)
        ht.insert(k1, "v1")
        ht.insert(k2, "v2")
        ht.delete(k1)
        assert ht.find(k2) == "v2"
        with pytest.raises(KeyNotFoundError):
            ht.find(k1)

    def test_two_keys_same_slot_delete_second(self, ht: ProbingHashTable):
        k1 = _FixedHashKey("alpha", 0)
        k2 = _FixedHashKey("beta", 0)
        ht.insert(k1, "v1")
        ht.insert(k2, "v2")
        ht.delete(k2)
        assert ht.find(k1) == "v1"
        with pytest.raises(KeyNotFoundError):
            ht.find(k2)

    def test_probing_wraps_around(self):
        ht = ProbingHashTable(initial_capacity=4, load_factor_threshold=1.0)
        k1 = _FixedHashKey("a", 3)
        k2 = _FixedHashKey("b", 3)
        k3 = _FixedHashKey("c", 3)
        ht.insert(k1, "v1")
        ht.insert(k2, "v2")
        ht.insert(k3, "v3")
        assert ht.find(k1) == "v1"
        assert ht.find(k2) == "v2"
        assert ht.find(k3) == "v3"

    def test_insert_after_delete_reuses_deleted_slot(self, ht: ProbingHashTable):
        k1 = _FixedHashKey("alpha", 0)
        k2 = _FixedHashKey("beta", 0)
        k3 = _FixedHashKey("gamma", 0)
        ht.insert(k1, "v1")
        ht.insert(k2, "v2")
        ht.delete(k1)
        ht.insert(k3, "v3")
        assert ht.find(k2) == "v2"
        assert ht.find(k3) == "v3"
        with pytest.raises(KeyNotFoundError):
            ht.find(k1)


class TestRehash:
    def test_rehash_preserves_data(self, ht: ProbingHashTable):
        for i in range(20):
            ht.insert(i, i * 100)
        for i in range(20):
            assert ht.find(i) == i * 100

    def test_rehash_clears_deleted_markers(self):
        ht = ProbingHashTable(initial_capacity=8, load_factor_threshold=1.0)
        for i in range(6):
            ht.insert(i, i * 10)
        assert ht.capacity() == 8
        for i in range(5):
            ht.delete(i)
        assert ht.deleted_count() == 5
        assert ht.size() == 1
        assert ht.capacity() == 8
        ht.insert("trigger", "rehash")
        assert ht.deleted_count() == 0
        assert ht.find(5) == 50
        assert ht.find("trigger") == "rehash"

    def test_rehash_triggers_on_load_factor(self):
        ht = ProbingHashTable(initial_capacity=4, load_factor_threshold=0.75)
        ht.insert("a", 1)
        ht.insert("b", 2)
        ht.insert("c", 3)
        assert ht.capacity() == 4
        assert ht.size() == 3
        ht.insert("d", 4)
        assert ht.capacity() == 8

    def test_rehash_triggers_on_full_table(self):
        ht = ProbingHashTable(initial_capacity=4, load_factor_threshold=1.0)
        ht.insert("a", 1)
        ht.insert("b", 2)
        ht.insert("c", 3)
        ht.insert("d", 4)
        assert ht.size() == 4
        ht.insert("e", 5)
        assert ht.size() == 5
        assert ht.capacity() >= 5
        for k, v in [("a", 1), ("b", 2), ("c", 3), ("d", 4), ("e", 5)]:
            assert ht.find(k) == v

    def test_rehash_from_deleted_marker_pressure(self):
        ht = ProbingHashTable(initial_capacity=8, load_factor_threshold=1.0)
        for i in range(6):
            ht.insert(i, i)
        assert ht.capacity() == 8
        for i in range(4):
            ht.delete(i)
        assert ht.deleted_count() >= 4
        assert ht.deleted_count() >= ht.size()
        ht.insert(100, 100)
        assert ht.deleted_count() == 0
        assert ht.find(4) == 4
        assert ht.find(5) == 5
        assert ht.find(100) == 100

    def test_no_unnecessary_rehash_when_empty_slots_plentiful(self):
        ht = ProbingHashTable(initial_capacity=16, load_factor_threshold=0.75)
        for i in range(3):
            ht.insert(i, i * 10)
        for i in range(2):
            ht.delete(i)
        assert ht.deleted_count() == 2
        assert ht.size() == 1
        cap_before = ht.capacity()
        deleted_before = ht.deleted_count()
        ht.insert(100, 1000)
        assert ht.capacity() == cap_before
        assert ht.deleted_count() <= deleted_before
        assert ht.find(2) == 20
        assert ht.find(100) == 1000

    def test_cleanup_triggers_even_within_load_threshold(self):
        ht = ProbingHashTable(initial_capacity=16, load_factor_threshold=0.75)
        for i in range(8):
            ht.insert(i, i * 10)
        for i in range(6):
            ht.delete(i)
        assert ht.size() == 2
        assert ht.deleted_count() == 6
        assert ht.capacity() == 16
        assert ht.load_factor() == pytest.approx(2 / 16)
        ht.insert(100, 1000)
        assert ht.deleted_count() == 0
        assert ht.size() == 3
        assert ht.capacity() == 16
        assert ht.find(6) == 60
        assert ht.find(7) == 70
        assert ht.find(100) == 1000


class TestConsecutiveDeletion:
    def test_many_deletions_then_operations(self, ht: ProbingHashTable):
        for i in range(7):
            ht.insert(i, i * 10)
        for i in range(6):
            ht.delete(i)
        assert ht.size() == 1
        assert ht.deleted_count() == 6
        assert ht.find(6) == 60
        with pytest.raises(KeyNotFoundError):
            ht.find(0)

    def test_insert_after_mass_deletion(self, ht: ProbingHashTable):
        for i in range(7):
            ht.insert(i, i * 10)
        for i in range(6):
            ht.delete(i)
        ht.insert(100, 1000)
        assert ht.find(100) == 1000
        assert ht.find(6) == 60

    def test_repeated_insert_delete_cycles(self, ht: ProbingHashTable):
        for cycle in range(3):
            for i in range(5):
                ht.insert(f"key_{cycle}_{i}", cycle * 10 + i)
            for i in range(4):
                ht.delete(f"key_{cycle}_{i}")
        assert ht.size() == 3
        for cycle in range(3):
            assert ht.find(f"key_{cycle}_4") == cycle * 10 + 4


class TestExpansion:
    def test_capacity_doubles_on_expand(self):
        ht = ProbingHashTable(initial_capacity=4, load_factor_threshold=0.75)
        assert ht.capacity() == 4
        ht.insert("a", 1)
        ht.insert("b", 2)
        ht.insert("c", 3)
        assert ht.capacity() == 4
        ht.insert("d", 4)
        assert ht.capacity() == 8

    def test_all_data_preserved_after_expand(self):
        ht = ProbingHashTable(initial_capacity=4, load_factor_threshold=0.75)
        data = {chr(ord("a") + i): i for i in range(10)}
        for k, v in data.items():
            ht.insert(k, v)
        for k, v in data.items():
            assert ht.find(k) == v

    def test_update_does_not_trigger_expand(self):
        ht = ProbingHashTable(initial_capacity=4, load_factor_threshold=0.75)
        ht.insert("a", 1)
        ht.insert("b", 2)
        cap_before = ht.capacity()
        ht.insert("a", 100)
        assert ht.capacity() == cap_before
        assert ht.find("a") == 100


class TestSizeAndState:
    def test_size_tracking(self, ht: ProbingHashTable):
        assert ht.size() == 0
        ht.insert("a", 1)
        assert ht.size() == 1
        ht.insert("b", 2)
        assert ht.size() == 2
        ht.delete("a")
        assert ht.size() == 1

    def test_is_empty(self, ht: ProbingHashTable):
        assert ht.is_empty() is True
        ht.insert("a", 1)
        assert ht.is_empty() is False
        ht.delete("a")
        assert ht.is_empty() is True

    def test_len_dunder(self, ht: ProbingHashTable):
        assert len(ht) == 0
        ht.insert("a", 1)
        assert len(ht) == 1

    def test_repr(self, ht: ProbingHashTable):
        ht.insert("a", 1)
        r = repr(ht)
        assert "'a'" in r
        assert "1" in r

    def test_load_factor(self, ht: ProbingHashTable):
        assert ht.load_factor() == 0.0
        ht.insert("a", 1)
        assert ht.load_factor() == pytest.approx(1 / 8)


class TestInvalidConstruction:
    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError):
            ProbingHashTable(initial_capacity=0)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError):
            ProbingHashTable(initial_capacity=-1)

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError):
            ProbingHashTable(load_factor_threshold=0)

    def test_threshold_above_one_raises(self):
        with pytest.raises(ValueError):
            ProbingHashTable(load_factor_threshold=1.5)


class TestVariousKeyTypes:
    def test_integer_keys(self, ht: ProbingHashTable):
        ht.insert(1, "one")
        ht.insert(2, "two")
        assert ht.find(1) == "one"
        assert ht.find(2) == "two"

    def test_mixed_key_types(self, ht: ProbingHashTable):
        ht.insert(1, "int")
        ht.insert("1", "str")
        assert ht.find(1) == "int"
        assert ht.find("1") == "str"

    def test_none_key(self, ht: ProbingHashTable):
        ht.insert(None, "null_value")
        assert ht.find(None) == "null_value"
