from __future__ import annotations

import pytest

from solocoder_py.hashtable_chaining import HashTable


class TestHashTableCreation:
    def test_default_creation(self):
        ht = HashTable()
        assert ht.size() == 0
        assert ht.capacity == 8
        assert ht.load_factor_threshold == 0.75

    def test_custom_capacity(self):
        ht = HashTable(initial_capacity=16)
        assert ht.capacity == 16
        assert ht.size() == 0

    def test_custom_load_factor(self):
        ht = HashTable(load_factor_threshold=0.5)
        assert ht.load_factor_threshold == 0.5

    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError, match="positive"):
            HashTable(initial_capacity=0)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError, match="positive"):
            HashTable(initial_capacity=-1)

    def test_zero_load_factor_raises(self):
        with pytest.raises(ValueError, match="0, 1]"):
            HashTable(load_factor_threshold=0)

    def test_negative_load_factor_raises(self):
        with pytest.raises(ValueError, match="0, 1]"):
            HashTable(load_factor_threshold=-0.5)

    def test_load_factor_greater_than_one_raises(self):
        with pytest.raises(ValueError, match="0, 1]"):
            HashTable(load_factor_threshold=1.5)

    def test_load_factor_one_is_valid(self):
        ht = HashTable(load_factor_threshold=1.0)
        assert ht.load_factor_threshold == 1.0


class TestPutAndGet:
    def test_put_single_key(self, empty_ht):
        empty_ht.put("key", "value")
        assert empty_ht.get("key") == "value"
        assert empty_ht.size() == 1

    def test_put_multiple_keys(self, empty_ht):
        empty_ht.put("a", 1)
        empty_ht.put("b", 2)
        empty_ht.put("c", 3)
        assert empty_ht.get("a") == 1
        assert empty_ht.get("b") == 2
        assert empty_ht.get("c") == 3
        assert empty_ht.size() == 3

    def test_put_update_existing_key(self, empty_ht):
        empty_ht.put("key", "old_value")
        empty_ht.put("key", "new_value")
        assert empty_ht.get("key") == "new_value"
        assert empty_ht.size() == 1

    def test_put_update_multiple_times(self, empty_ht):
        empty_ht.put("x", 1)
        empty_ht.put("x", 2)
        empty_ht.put("x", 3)
        assert empty_ht.get("x") == 3
        assert empty_ht.size() == 1

    def test_get_nonexistent_key_raises(self, empty_ht):
        with pytest.raises(KeyError, match="nonexistent"):
            empty_ht.get("nonexistent")

    def test_put_with_collisions(self):
        ht = HashTable[int, str](initial_capacity=4)
        ht.put(1, "one")
        ht.put(5, "five")
        ht.put(9, "nine")
        assert ht.get(1) == "one"
        assert ht.get(5) == "five"
        assert ht.get(9) == "nine"
        assert ht.size() == 3

    def test_integer_keys(self, empty_ht):
        empty_ht.put(42, "answer")
        assert empty_ht.get(42) == "answer"

    def test_string_keys(self, empty_ht):
        empty_ht.put("hello", "world")
        assert empty_ht.get("hello") == "world"

    def test_none_value(self, empty_ht):
        empty_ht.put("key", None)
        assert empty_ht.get("key") is None
        assert empty_ht.size() == 1


class TestRemove:
    def test_remove_existing_key(self, small_ht):
        result = small_ht.remove("apple")
        assert result == 1
        assert small_ht.size() == 2
        assert "apple" not in small_ht

    def test_remove_last_key(self):
        ht = HashTable[str, int]()
        ht.put("only", 42)
        result = ht.remove("only")
        assert result == 42
        assert ht.size() == 0

    def test_remove_nonexistent_key_raises(self, small_ht):
        with pytest.raises(KeyError, match="nonexistent"):
            small_ht.remove("nonexistent")

    def test_remove_from_empty_raises(self, empty_ht):
        with pytest.raises(KeyError, match="missing"):
            empty_ht.remove("missing")

    def test_remove_and_reinsert(self, small_ht):
        small_ht.remove("banana")
        assert "banana" not in small_ht
        small_ht.put("banana", 99)
        assert small_ht.get("banana") == 99
        assert small_ht.size() == 3

    def test_remove_key_with_collisions(self):
        ht = HashTable[int, str](initial_capacity=4)
        ht.put(1, "one")
        ht.put(5, "five")
        ht.put(9, "nine")
        ht.remove(5)
        assert ht.get(1) == "one"
        assert ht.get(9) == "nine"
        with pytest.raises(KeyError):
            ht.get(5)
        assert ht.size() == 2

    def test_remove_head_of_chain(self):
        ht = HashTable[int, str](initial_capacity=4)
        ht.put(1, "one")
        ht.put(5, "five")
        ht.remove(1)
        assert ht.get(5) == "five"
        assert ht.size() == 1

    def test_remove_then_update_does_not_recreate(self):
        ht = HashTable[str, int]()
        ht.put("a", 1)
        ht.remove("a")
        ht.put("a", 2)
        assert ht.get("a") == 2
        assert ht.size() == 1


class TestContains:
    def test_contains_existing_key(self, small_ht):
        assert small_ht.contains("apple") is True
        assert "banana" in small_ht

    def test_contains_nonexistent_key(self, small_ht):
        assert small_ht.contains("missing") is False
        assert "nonexistent" not in small_ht

    def test_contains_empty_table(self, empty_ht):
        assert empty_ht.contains("anything") is False

    def test_contains_after_remove(self, small_ht):
        small_ht.remove("cherry")
        assert small_ht.contains("cherry") is False
        assert small_ht.contains("apple") is True


class TestSizeAndLoadFactor:
    def test_initial_size_zero(self, empty_ht):
        assert empty_ht.size() == 0
        assert len(empty_ht) == 0

    def test_size_after_puts(self, small_ht):
        assert small_ht.size() == 3
        assert len(small_ht) == 3

    def test_size_after_updates(self, small_ht):
        small_ht.put("apple", 100)
        assert small_ht.size() == 3

    def test_size_after_remove(self, small_ht):
        small_ht.remove("banana")
        assert small_ht.size() == 2

    def test_load_factor_empty(self, empty_ht):
        assert empty_ht.load_factor() == 0.0

    def test_load_factor_partial(self, empty_ht):
        empty_ht.put("a", 1)
        assert empty_ht.load_factor() == 1 / 8

    def test_load_factor_half_full(self, empty_ht):
        for i in range(4):
            empty_ht.put(f"key_{i}", i)
        assert empty_ht.load_factor() == 4 / 8

    def test_load_factor_threshold_property(self):
        ht = HashTable(load_factor_threshold=0.6)
        assert ht.load_factor_threshold == 0.6


class TestResizing:
    def test_resize_triggers_when_load_factor_exceeds_threshold(self):
        ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=0.75)
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        assert ht.capacity == 4
        ht.put("d", 4)
        assert ht.capacity == 8
        assert ht.size() == 4

    def test_data_intact_after_resize(self):
        ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=0.75)
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        ht.put("d", 4)
        assert ht.capacity == 8
        assert ht.get("a") == 1
        assert ht.get("b") == 2
        assert ht.get("c") == 3
        assert ht.get("d") == 4

    def test_multiple_resizes(self):
        ht = HashTable[str, int](initial_capacity=2, load_factor_threshold=0.75)
        for i in range(20):
            ht.put(f"key_{i}", i)
        assert ht.capacity > 2
        assert ht.size() == 20
        for i in range(20):
            assert ht.get(f"key_{i}") == i

    def test_large_number_of_insertions(self):
        ht = HashTable[int, int]()
        for i in range(100):
            ht.put(i, i * 10)
        assert ht.size() == 100
        for i in range(100):
            assert ht.get(i) == i * 10

    def test_resize_load_factor_below_threshold_after(self):
        ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=0.75)
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        ht.put("d", 4)
        assert ht.capacity == 8
        assert ht.load_factor() <= ht.load_factor_threshold

    def test_get_during_resize(self):
        ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=0.75)
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        assert ht.get("a") == 1
        assert ht.capacity == 4
        ht.put("d", 4)
        assert ht.capacity == 8
        assert ht.get("a") == 1
        assert ht.get("b") == 2
        assert ht.get("c") == 3
        assert ht.get("d") == 4

    def test_update_after_resize(self):
        ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=0.75)
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        ht.put("d", 4)
        assert ht.capacity == 8
        ht.put("a", 100)
        assert ht.get("a") == 100
        assert ht.size() == 4

    def test_remove_after_resize(self):
        ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=0.75)
        ht.put("a", 1)
        ht.put("b", 2)
        ht.put("c", 3)
        ht.put("d", 4)
        assert ht.capacity == 8
        ht.remove("b")
        assert ht.size() == 3
        assert "b" not in ht
        assert ht.get("a") == 1
        assert ht.get("c") == 3
        assert ht.get("d") == 4


class TestThresholdBoundary:
    def test_no_resize_when_load_factor_at_threshold(self):
        ht = HashTable[str, int](initial_capacity=8, load_factor_threshold=0.75)
        for i in range(6):
            ht.put(f"key_{i}", i)
        assert ht.capacity == 8
        assert ht.size() == 6
        assert ht.load_factor() == 6 / 8

    def test_resize_when_load_factor_just_above_threshold(self):
        ht = HashTable[str, int](initial_capacity=8, load_factor_threshold=0.75)
        for i in range(7):
            ht.put(f"key_{i}", i)
        assert ht.capacity == 16
        assert ht.size() == 7

    def test_threshold_exactly_one(self):
        ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=1.0)
        for i in range(4):
            ht.put(f"key_{i}", i)
        assert ht.capacity == 4
        ht.put("key_4", 4)
        assert ht.capacity == 8
        assert ht.size() == 5

    def test_exact_threshold_boundary(self):
        ht = HashTable[str, int](initial_capacity=10, load_factor_threshold=0.5)
        for i in range(5):
            ht.put(f"key_{i}", i)
        assert ht.capacity == 10
        ht.put("key_5", 5)
        assert ht.capacity == 20
        assert ht.size() == 6


class TestEmptyTableOperations:
    def test_get_on_empty_raises(self, empty_ht):
        with pytest.raises(KeyError):
            empty_ht.get("anything")

    def test_remove_on_empty_raises(self, empty_ht):
        with pytest.raises(KeyError):
            empty_ht.remove("anything")

    def test_contains_on_empty_false(self, empty_ht):
        assert empty_ht.contains("key") is False

    def test_size_empty_zero(self, empty_ht):
        assert empty_ht.size() == 0

    def test_load_factor_empty_zero(self, empty_ht):
        assert empty_ht.load_factor() == 0.0

    def test_put_on_empty(self, empty_ht):
        empty_ht.put("first", 1)
        assert empty_ht.size() == 1
        assert empty_ht.get("first") == 1


class TestDictionaryStyleAccess:
    def test_getitem(self, small_ht):
        assert small_ht["apple"] == 1

    def test_getitem_missing_raises(self, small_ht):
        with pytest.raises(KeyError):
            _ = small_ht["missing"]

    def test_setitem(self, empty_ht):
        empty_ht["key"] = "value"
        assert empty_ht["key"] == "value"

    def test_setitem_update(self, small_ht):
        small_ht["banana"] = 99
        assert small_ht["banana"] == 99
        assert small_ht.size() == 3

    def test_len(self, small_ht):
        assert len(small_ht) == 3

    def test_contains_operator(self, small_ht):
        assert "cherry" in small_ht
        assert "durian" not in small_ht


class TestEdgeCases:
    def test_empty_string_key(self, empty_ht):
        empty_ht.put("", "empty_key")
        assert empty_ht.get("") == "empty_key"

    def test_very_long_key(self, empty_ht):
        long_key = "a" * 10000
        empty_ht.put(long_key, "long")
        assert empty_ht.get(long_key) == "long"

    def test_special_character_keys(self, empty_ht):
        special_keys = ["!@#$%^&*()", "key with spaces", "日本語", "emoji_🎉", "tab\tkey"]
        for i, key in enumerate(special_keys):
            empty_ht.put(key, i)
        for i, key in enumerate(special_keys):
            assert empty_ht.get(key) == i

    def test_numeric_key_types(self):
        ht = HashTable[float, str]()
        ht.put(3.14, "pi")
        ht.put(2.718, "e")
        assert ht.get(3.14) == "pi"
        assert ht.get(2.718) == "e"

    def test_tuple_keys(self):
        ht = HashTable[tuple[int, int], str]()
        ht.put((1, 2), "a")
        ht.put((3, 4), "b")
        assert ht.get((1, 2)) == "a"
        assert ht.get((3, 4)) == "b"

    def test_large_values(self, empty_ht):
        large_value = "x" * 100000
        empty_ht.put("big", large_value)
        assert empty_ht.get("big") == large_value

    def test_many_updates_same_key(self, empty_ht):
        for i in range(1000):
            empty_ht.put("key", i)
        assert empty_ht.get("key") == 999
        assert empty_ht.size() == 1

    def test_alternating_put_remove(self, empty_ht):
        for i in range(100):
            empty_ht.put(f"key_{i}", i)
        for i in range(50):
            empty_ht.remove(f"key_{i}")
        assert empty_ht.size() == 50
        for i in range(50):
            assert f"key_{i}" not in empty_ht
        for i in range(50, 100):
            assert empty_ht.get(f"key_{i}") == i
