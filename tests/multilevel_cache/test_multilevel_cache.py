from __future__ import annotations

import threading
import time
from typing import Dict

import pytest

from solocoder_py.multilevel_cache import (
    DataSourceError,
    InvalidCapacityError,
    MultiLevelCache,
)


class MockDataSource:
    def __init__(self, data: Dict[str, str], should_fail: bool = False) -> None:
        self.data = data
        self.should_fail = should_fail
        self.load_count = 0

    def load(self, key: str) -> str:
        self.load_count += 1
        if self.should_fail:
            raise RuntimeError("Data source failure")
        if key not in self.data:
            raise KeyError(f"Key not found: {key}")
        return self.data[key]


class TestNormalFlow:
    def test_l1_hit_direct_return(self):
        data_source = MockDataSource({"a": "1", "b": "2"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("a")
        assert cache.has_in_l1("a") is True
        assert cache.has_in_l2("a") is True

        data_source.load_count = 0
        cache.clear()

        cache.get("a")
        assert data_source.load_count == 1

        data_source.load_count = 0

        result = cache.get("a")
        assert result == "1"
        assert data_source.load_count == 0
        assert cache.has_in_l1("a") is True
        assert cache.has_in_l2("a") is True

        stats = cache.stats
        assert stats.l1_hits >= 1
        assert stats.l2_hits == 0

    def test_l2_hit_backfill_to_l1(self):
        data_source = MockDataSource({"a": "1", "b": "2", "c": "3"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("a")
        cache.get("b")
        data_source.load_count = 0
        cache._l1.clear()

        assert cache.has_in_l1("a") is False
        assert cache.has_in_l2("a") is True

        result = cache.get("a")
        assert result == "1"
        assert data_source.load_count == 0
        assert cache.has_in_l1("a") is True

        stats = cache.stats
        assert stats.l2_hits >= 1

    def test_both_miss_penetrate_and_backfill(self):
        data_source = MockDataSource({"x": "100"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        assert cache.has_in_l1("x") is False
        assert cache.has_in_l2("x") is False

        result = cache.get("x")
        assert result == "100"
        assert data_source.load_count == 1
        assert cache.has_in_l1("x") is True
        assert cache.has_in_l2("x") is True

        stats = cache.stats
        assert stats.l1_misses >= 1
        assert stats.l2_misses >= 1
        assert stats.data_source_loads == 1

    def test_second_read_hits_l1(self):
        data_source = MockDataSource({"y": "200"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("y")
        data_source.load_count = 0

        result = cache.get("y")
        assert result == "200"
        assert data_source.load_count == 0
        assert cache.stats.l1_hits >= 1


class TestBoundaryConditions:
    def test_l1_full_triggers_eviction(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(5)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=10, data_source=data_source)

        cache.get("k0")
        cache.get("k1")
        assert cache.l1_size == 2

        cache.get("k2")
        assert cache.l1_size == 2
        assert cache.has_in_l1("k2") is True

        assert cache.has_in_l2("k0") is True
        assert cache.has_in_l2("k1") is True
        assert cache.has_in_l2("k2") is True

    def test_l1_eviction_does_not_affect_l2(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(4)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=10, data_source=data_source)

        cache.get("k0")
        cache.get("k1")
        cache.get("k2")
        cache.get("k3")

        assert cache.l2_size == 4
        for i in range(4):
            assert cache.has_in_l2(f"k{i}") is True

    def test_l2_full_triggers_eviction(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(6)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=3, data_source=data_source)

        cache.get("k0")
        cache.get("k1")
        cache.get("k2")
        assert cache.l2_size == 3

        cache.get("k3")
        assert cache.l2_size == 3

        stats = cache.stats
        assert stats.evictions_l2 >= 1

    def test_l2_eviction_does_not_affect_l1(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(5)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=3, data_source=data_source)

        cache.get("k0")
        cache.get("k1")
        assert cache.has_in_l1("k0") is True
        assert cache.has_in_l1("k1") is True

        cache.get("k2")
        cache.get("k3")
        cache.get("k4")

        assert cache.has_in_l1("k3") is True
        assert cache.has_in_l1("k4") is True

    def test_write_invalidation_removes_from_both_levels(self):
        data_source = MockDataSource({"a": "1"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("a")
        assert cache.has_in_l1("a") is True
        assert cache.has_in_l2("a") is True

        cache.set("a", "2")

        assert cache.has_in_l1("a") is False
        assert cache.has_in_l2("a") is False

        data_source.data["a"] = "2"
        result = cache.get("a")
        assert result == "2"
        assert data_source.load_count == 2

    def test_update_then_read_returns_new_value(self):
        data_source = MockDataSource({"x": "old"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        assert cache.get("x") == "old"

        data_source.data["x"] = "new"
        cache.set("x", "new")

        assert cache.get("x") == "new"
        assert cache.get("x") == "new"

    def test_l1_evicted_then_backfilled_from_l2(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(3)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=10, data_source=data_source)

        cache.get("k0")
        cache.get("k1")
        cache.get("k2")

        assert cache.has_in_l1("k0") is False
        assert cache.has_in_l2("k0") is True

        data_source.load_count = 0
        result = cache.get("k0")
        assert result == "v0"
        assert data_source.load_count == 0
        assert cache.has_in_l1("k0") is True


class TestExceptionBranches:
    def test_data_source_failure_no_write_to_either_level(self):
        failing_source = MockDataSource({"a": "1"}, should_fail=True)
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=failing_source)

        with pytest.raises(DataSourceError, match="Failed to load from data source"):
            cache.get("a")

        assert cache.has_in_l1("a") is False
        assert cache.has_in_l2("a") is False
        assert cache.l1_size == 0
        assert cache.l2_size == 0

    def test_data_source_failure_propagates_original_exception(self):
        failing_source = MockDataSource({}, should_fail=True)
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=failing_source)

        with pytest.raises(DataSourceError) as exc_info:
            cache.get("missing")

        assert "Data source failure" in str(exc_info.value.__cause__)

    def test_no_data_source_configured_raises(self):
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5)

        with pytest.raises(DataSourceError, match="No data source configured"):
            cache.get("anything")

    def test_repeated_eviction_and_backfill_consistency(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(5)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        for round in range(3):
            for i in range(5):
                result = cache.get(f"k{i}")
                assert result == f"v{i}"

        data_source.load_count = 0
        for i in range(5):
            result = cache.get(f"k{i}")
            assert result == f"v{i}"
        assert data_source.load_count == 0

    def test_key_not_found_in_data_source(self):
        data_source = MockDataSource({"a": "1"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        with pytest.raises(DataSourceError):
            cache.get("nonexistent")

        assert cache.has_in_l1("nonexistent") is False
        assert cache.has_in_l2("nonexistent") is False


class TestIndependentEviction:
    def test_l1_and_l2_eviction_counts_are_independent(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(10)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        for i in range(10):
            cache.get(f"k{i}")

        stats = cache.stats
        assert stats.evictions_l1 >= 7
        assert stats.evictions_l2 >= 4
        assert stats.evictions_l1 != stats.evictions_l2

    def test_l1_eviction_preserves_l2_data(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(4)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=10, data_source=data_source)

        cache.get("k0")
        cache.get("k1")
        cache.get("k2")

        assert cache.has_in_l1("k0") is False
        assert cache.has_in_l2("k0") is True

        data_source.load_count = 0
        assert cache.get("k0") == "v0"
        assert data_source.load_count == 0

    def test_l2_eviction_preserves_l1_data(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(6)})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=3, data_source=data_source)

        cache.get("k0")
        cache.get("k1")

        cache.get("k2")
        cache.get("k3")
        cache.get("k4")

        assert cache.has_in_l1("k3") is True
        assert cache.has_in_l1("k4") is True
        data_source.load_count = 0
        assert cache.get("k3") == "v3"
        assert cache.get("k4") == "v4"
        assert data_source.load_count == 0


class TestInvalidateOperation:
    def test_invalidate_removes_from_both_levels(self):
        data_source = MockDataSource({"a": "1"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("a")
        cache.invalidate("a")

        assert cache.has_in_l1("a") is False
        assert cache.has_in_l2("a") is False

    def test_invalidate_nonexistent_key_no_error(self):
        data_source = MockDataSource({"a": "1"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.invalidate("nonexistent")
        assert cache.delete("nonexistent") is False

    def test_delete_returns_true_if_existed_in_any_level(self):
        data_source = MockDataSource({"a": "1"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("a")
        assert cache.delete("a") is True
        assert cache.delete("a") is False


class TestConstructorValidation:
    def test_l1_capacity_must_be_positive(self):
        with pytest.raises(ValueError, match="l1_capacity must be positive"):
            MultiLevelCache[str, str](l1_capacity=0, l2_capacity=5)

    def test_l2_capacity_must_be_positive(self):
        with pytest.raises(ValueError, match="l2_capacity must be positive"):
            MultiLevelCache[str, str](l1_capacity=2, l2_capacity=0)

    def test_l1_must_be_less_than_l2(self):
        with pytest.raises(ValueError, match="l1_capacity must be less than l2_capacity"):
            MultiLevelCache[str, str](l1_capacity=5, l2_capacity=5)

        with pytest.raises(ValueError, match="l1_capacity must be less than l2_capacity"):
            MultiLevelCache[str, str](l1_capacity=5, l2_capacity=3)

    def test_lru_cache_invalid_capacity(self):
        from solocoder_py.multilevel_cache import LRUCache

        with pytest.raises(InvalidCapacityError, match="capacity must be non-negative"):
            LRUCache(capacity=-1)


class TestClearOperation:
    def test_clear_resets_both_levels(self):
        data_source = MockDataSource({"a": "1", "b": "2"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("a")
        cache.get("b")
        assert cache.l1_size == 2
        assert cache.l2_size == 2

        cache.clear()
        assert cache.l1_size == 0
        assert cache.l2_size == 0
        assert cache.has_in_l1("a") is False
        assert cache.has_in_l2("b") is False

    def test_clear_resets_stats(self):
        data_source = MockDataSource({"a": "1"})
        cache = MultiLevelCache[str, str](l1_capacity=2, l2_capacity=5, data_source=data_source)

        cache.get("a")
        cache.get("a")
        assert cache.stats.l1_hits == 1
        assert cache.stats.data_source_loads == 1

        cache.clear()
        stats = cache.stats
        assert stats.l1_hits == 0
        assert stats.l2_hits == 0
        assert stats.data_source_loads == 0
        assert stats.evictions_l1 == 0
        assert stats.evictions_l2 == 0


class TestLRUCacheBasic:
    def test_lru_basic_operations(self):
        from solocoder_py.multilevel_cache import LRUCache

        cache: LRUCache[str, int] = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_eviction_order(self):
        from solocoder_py.multilevel_cache import LRUCache

        cache: LRUCache[str, int] = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        cache.set("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_lru_update_existing_key(self):
        from solocoder_py.multilevel_cache import LRUCache

        cache: LRUCache[str, int] = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("a", 2)

        assert cache.get("a") == 2
        assert cache.size == 1


class TestConcurrentAccess:
    def test_concurrent_reads_and_writes(self):
        data_source = MockDataSource({f"k{i}": f"v{i}" for i in range(20)})
        cache = MultiLevelCache[str, str](l1_capacity=5, l2_capacity=15, data_source=data_source)

        errors = []

        def reader():
            try:
                for i in range(20):
                    cache.get(f"k{i}")
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(20):
                    cache.set(f"k{i}", f"updated{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=reader))
            threads.append(threading.Thread(target=writer))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
