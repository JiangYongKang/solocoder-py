from __future__ import annotations

import threading

import pytest

from solocoder_py.counter import (
    DimensionPathError,
    DimensionSchema,
    DimensionStructureMismatchError,
    MergeError,
    MultiDimCounter,
)


class TestDimensionSchema:
    def test_schema_creation(self):
        schema = DimensionSchema(levels=["a", "b", "c"])
        assert schema.max_depth == 3
        assert schema.levels == ["a", "b", "c"]

    def test_validate_valid_path(self):
        schema = DimensionSchema(levels=["a", "b", "c"])
        schema.validate_path(["x"])
        schema.validate_path(["x", "y"])
        schema.validate_path(["x", "y", "z"])

    def test_validate_empty_path_raises(self):
        schema = DimensionSchema(levels=["a", "b"])
        with pytest.raises(DimensionPathError, match="cannot be empty"):
            schema.validate_path([])

    def test_validate_too_deep_path_raises(self):
        schema = DimensionSchema(levels=["a", "b"])
        with pytest.raises(DimensionPathError, match="exceeds max depth"):
            schema.validate_path(["x", "y", "z"])

    def test_validate_empty_segment_raises(self):
        schema = DimensionSchema(levels=["a", "b"])
        with pytest.raises(DimensionPathError, match="cannot be empty"):
            schema.validate_path(["x", ""])

    def test_is_full_path(self):
        schema = DimensionSchema(levels=["a", "b", "c"])
        assert schema.is_full_path(["x", "y", "z"]) is True
        assert schema.is_full_path(["x", "y"]) is False
        assert schema.is_full_path(["x"]) is False

    def test_level_name(self):
        schema = DimensionSchema(levels=["dc", "host", "service"])
        assert schema.level_name(1) == "dc"
        assert schema.level_name(2) == "host"
        assert schema.level_name(3) == "service"
        assert schema.level_name(0) is None
        assert schema.level_name(4) is None


class TestMultiDimCounterBasicOperations:
    def test_create_with_schema(self, three_level_schema):
        counter = MultiDimCounter(schema=three_level_schema)
        assert counter.max_depth == 3
        assert counter.schema.levels == ["datacenter", "host", "service"]

    def test_create_with_levels(self):
        counter = MultiDimCounter(levels=["a", "b"])
        assert counter.max_depth == 2
        assert counter.schema.levels == ["a", "b"]

    def test_create_both_schema_and_levels_raises(self, three_level_schema):
        with pytest.raises(ValueError, match="not both"):
            MultiDimCounter(schema=three_level_schema, levels=["a", "b"])

    def test_create_neither_schema_nor_levels_raises(self):
        with pytest.raises(ValueError, match="must be provided"):
            MultiDimCounter()

    def test_initial_total_is_zero(self, three_level_counter):
        assert three_level_counter.total() == 0

    def test_increment_single_full_path(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/api-service")
        assert three_level_counter.query("dc-east/host-01/api-service") == 1

    def test_increment_with_delta(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/api-service", 5)
        assert three_level_counter.query("dc-east/host-01/api-service") == 5

    def test_increment_partial_path_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="full dimension path is required"):
            three_level_counter.increment("dc-east/host-01", 3)

    def test_increment_top_level_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="full dimension path is required"):
            three_level_counter.increment("dc-east", 10)

    def test_decrement(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/api-service", 10)
        three_level_counter.decrement("dc-east/host-01/api-service", 3)
        assert three_level_counter.query("dc-east/host-01/api-service") == 7

    def test_decrement_negative_delta_raises(self, three_level_counter):
        with pytest.raises(ValueError, match="non-negative"):
            three_level_counter.decrement("dc-east/host-01/api-service", -1)

    def test_contains_operator(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/api-service")
        assert "dc-east/host-01/api-service" in three_level_counter
        assert "dc-east/host-01" in three_level_counter
        assert "dc-east" in three_level_counter
        assert "dc-west" not in three_level_counter

    def test_getitem_operator(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/api-service", 7)
        assert three_level_counter["dc-east/host-01/api-service"] == 7
        assert three_level_counter["dc-nonexistent"] == 0


class TestHierarchicalRollup:
    def test_increment_propagates_to_all_ancestors(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/api-service", 5)
        assert three_level_counter.query("dc-east/host-01/api-service") == 5
        assert three_level_counter.query("dc-east/host-01") == 5
        assert three_level_counter.query("dc-east") == 5

    def test_multiple_paths_aggregate_to_parent(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/api-service", 3)
        three_level_counter.increment("dc-east/host-01/web-service", 2)
        three_level_counter.increment("dc-east/host-02/api-service", 4)
        assert three_level_counter.query("dc-east/host-01/api-service") == 3
        assert three_level_counter.query("dc-east/host-01/web-service") == 2
        assert three_level_counter.query("dc-east/host-01") == 5
        assert three_level_counter.query("dc-east/host-02") == 4
        assert three_level_counter.query("dc-east") == 9
        assert three_level_counter.total() == 9

    def test_multiple_data_centers_total(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/service-a", 10)
        three_level_counter.increment("dc-west/host-01/service-b", 20)
        assert three_level_counter.query("dc-east") == 10
        assert three_level_counter.query("dc-west") == 20
        assert three_level_counter.total() == 30

    def test_query_children_top_level(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 1)
        three_level_counter.increment("dc-west/host-02/svc", 2)
        children = three_level_counter.query_children()
        assert children == {"dc-east": 1, "dc-west": 2}

    def test_query_children_mid_level(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 3)
        three_level_counter.increment("dc-east/host-01/svc-b", 5)
        three_level_counter.increment("dc-east/host-02/svc-a", 2)
        children = three_level_counter.query_children("dc-east")
        assert children == {"host-01": 8, "host-02": 2}

    def test_query_children_leaf_level(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 3)
        children = three_level_counter.query_children("dc-east/host-01")
        assert children == {"svc-a": 3}

    def test_query_children_empty(self, three_level_counter):
        children = three_level_counter.query_children("nonexistent")
        assert children == {}


class TestQueryBehavior:
    def test_query_nonexistent_top_level_returns_zero(self, three_level_counter):
        assert three_level_counter.query("dc-nonexistent") == 0

    def test_query_nonexistent_mid_level_returns_zero(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 5)
        assert three_level_counter.query("dc-east/host-99") == 0

    def test_query_nonexistent_leaf_returns_zero(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 5)
        assert three_level_counter.query("dc-east/host-01/svc-b") == 0

    def test_query_deeper_than_schema_returns_zero(self, three_level_counter):
        assert three_level_counter.query("a/b/c/d") == 0


class TestIncrementZeroDelta:
    def test_increment_zero_is_noop(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 0)
        assert three_level_counter.query("dc-east/host-01/svc") == 0
        assert "dc-east/host-01/svc" not in three_level_counter
        assert three_level_counter.total() == 0

    def test_increment_zero_does_not_create_nodes(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 0)
        assert three_level_counter.all_paths() == []


class TestPathValidation:
    def test_empty_path_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="cannot be empty"):
            three_level_counter.increment("", 1)

    def test_path_with_empty_segment_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="empty segment"):
            three_level_counter.increment("dc-east//svc", 1)

    def test_path_with_trailing_slash_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="empty segment"):
            three_level_counter.increment("dc-east/host-01/", 1)

    def test_path_with_leading_slash_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="empty segment"):
            three_level_counter.increment("/dc-east/host-01", 1)

    def test_skip_level_path_raises_three_level(self):
        counter = MultiDimCounter(levels=["dc", "host", "service"])
        with pytest.raises(DimensionPathError, match="full dimension path is required"):
            counter.increment("dc-east/api-service", 1)

    def test_deeper_than_max_depth_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="exceeds max depth"):
            three_level_counter.increment("a/b/c/d", 1)

    def test_non_string_path_raises(self, three_level_counter):
        with pytest.raises(DimensionPathError, match="must be a string"):
            three_level_counter.increment(123, 1)  # type: ignore

    def test_full_path_valid(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 1)
        assert three_level_counter.query("dc-east/host-01/svc-a") == 1

    def test_query_partial_path_valid(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 5)
        assert three_level_counter.query("dc-east/host-01") == 5
        assert three_level_counter.query("dc-east") == 5

    def test_query_skip_level_path_returns_zero(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 5)
        assert three_level_counter.query("dc-east/svc-a") == 0


class TestSingleLevelDimension:
    def test_single_level_increment(self, single_level_counter):
        single_level_counter.increment("region-a", 10)
        assert single_level_counter.query("region-a") == 10
        assert single_level_counter.total() == 10

    def test_single_level_no_children(self, single_level_counter):
        single_level_counter.increment("region-a", 5)
        children = single_level_counter.query_children("region-a")
        assert children == {}

    def test_single_level_query_children_top(self, single_level_counter):
        single_level_counter.increment("region-a", 3)
        single_level_counter.increment("region-b", 7)
        children = single_level_counter.query_children()
        assert children == {"region-a": 3, "region-b": 7}

    def test_single_level_full_path_valid(self, single_level_counter):
        single_level_counter.increment("region-x", 1)
        assert single_level_counter.query("region-x") == 1


class TestMaxDepthExtremePath:
    def test_max_depth_10_levels(self):
        levels = [f"level_{i}" for i in range(10)]
        counter = MultiDimCounter(levels=levels)
        path = "/".join(f"node_{i}" for i in range(10))
        counter.increment(path, 42)
        assert counter.query(path) == 42
        assert counter.query("/".join(f"node_{i}" for i in range(5))) == 42
        assert counter.query("node_0") == 42
        assert counter.total() == 42

    def test_11_levels_exceeds_10_depth(self):
        levels = [f"level_{i}" for i in range(10)]
        counter = MultiDimCounter(levels=levels)
        path = "/".join(f"node_{i}" for i in range(11))
        with pytest.raises(DimensionPathError, match="exceeds max depth"):
            counter.increment(path, 1)

    def test_9_levels_skipped_in_10_depth_schema_raises(self):
        levels = [f"level_{i}" for i in range(10)]
        counter = MultiDimCounter(levels=levels)
        path = "/".join(f"node_{i}" for i in range(9))
        with pytest.raises(DimensionPathError, match="full dimension path is required"):
            counter.increment(path, 1)


class TestMergeOperations:
    def test_merge_two_counters_same_paths(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)
        c1.increment("dc-east/host-01/svc", 3)
        c2.increment("dc-east/host-01/svc", 5)
        c1.merge(c2)
        assert c1.query("dc-east/host-01/svc") == 8
        assert c1.query("dc-east/host-01") == 8
        assert c1.query("dc-east") == 8

    def test_merge_two_counters_different_paths(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)
        c1.increment("dc-east/host-01/svc-a", 3)
        c2.increment("dc-west/host-02/svc-b", 5)
        c1.merge(c2)
        assert c1.query("dc-east/host-01/svc-a") == 3
        assert c1.query("dc-west/host-02/svc-b") == 5
        assert c1.query("dc-east") == 3
        assert c1.query("dc-west") == 5
        assert c1.total() == 8

    def test_merge_preserves_other_counter(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)
        c1.increment("dc-east/host-01/svc", 3)
        c2.increment("dc-east/host-01/svc", 5)
        c1.merge(c2)
        assert c2.query("dc-east/host-01/svc") == 5

    def test_merge_different_schemas_raises(self):
        c1 = MultiDimCounter(levels=["a", "b"])
        c2 = MultiDimCounter(levels=["x", "y", "z"])
        with pytest.raises(DimensionStructureMismatchError, match="different dimension schemas"):
            c1.merge(c2)

    def test_merge_same_schema_different_names_raises(self):
        c1 = MultiDimCounter(levels=["dc", "host"])
        c2 = MultiDimCounter(levels=["region", "server"])
        with pytest.raises(DimensionStructureMismatchError, match="different dimension schemas"):
            c1.merge(c2)

    def test_merge_wrong_type_raises(self, three_level_counter):
        with pytest.raises(MergeError, match="can only merge with another"):
            three_level_counter.merge("not a counter")  # type: ignore

    def test_merge_three_counters(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)
        c3 = MultiDimCounter(schema=three_level_schema)
        c1.increment("dc-a/h-1/s-1", 1)
        c2.increment("dc-a/h-1/s-2", 2)
        c3.increment("dc-b/h-2/s-3", 3)
        c1.merge(c2)
        c1.merge(c3)
        assert c1.query("dc-a/h-1/s-1") == 1
        assert c1.query("dc-a/h-1/s-2") == 2
        assert c1.query("dc-b/h-2/s-3") == 3
        assert c1.query("dc-a/h-1") == 3
        assert c1.query("dc-a") == 3
        assert c1.query("dc-b") == 3
        assert c1.total() == 6

    def test_merge_empty_counter(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)
        c1.increment("dc-east/host-01/svc", 5)
        c2.merge(c1)
        assert c2.query("dc-east/host-01/svc") == 5
        assert c2.total() == 5

    def test_merge_into_empty_counter(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)
        c2.increment("dc-east/host-01/svc", 5)
        c1.merge(c2)
        assert c1.query("dc-east/host-01/svc") == 5
        assert c1.total() == 5


class TestNegativeCounterBehavior:
    def test_decrement_below_zero_clamps(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 5)
        three_level_counter.decrement("dc-east/host-01/svc", 10)
        assert three_level_counter.query("dc-east/host-01/svc") == 0
        assert three_level_counter.query("dc-east/host-01") == 0
        assert three_level_counter.query("dc-east") == 0
        assert three_level_counter.total() == 0

    def test_negative_increment_clamps_to_zero(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", -5)
        assert three_level_counter.query("dc-east/host-01/svc") == 0
        assert three_level_counter.total() == 0

    def test_partial_decrement(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 10)
        three_level_counter.increment("dc-east/host-01/svc-b", 10)
        three_level_counter.decrement("dc-east/host-01/svc-a", 3)
        assert three_level_counter.query("dc-east/host-01/svc-a") == 7
        assert three_level_counter.query("dc-east/host-01/svc-b") == 10
        assert three_level_counter.query("dc-east/host-01") == 17
        assert three_level_counter.query("dc-east") == 17


class TestStateSerialization:
    def test_get_state_and_from_state(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 5)
        three_level_counter.increment("dc-west/host-02/svc", 3)
        state = three_level_counter.get_state()
        restored = MultiDimCounter.from_state(state)
        assert restored.query("dc-east/host-01/svc") == 5
        assert restored.query("dc-west/host-02/svc") == 3
        assert restored.query("dc-east") == 5
        assert restored.total() == 8

    def test_state_independent_of_original(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 5)
        state = three_level_counter.get_state()
        restored = MultiDimCounter.from_state(state)
        three_level_counter.increment("dc-east/host-01/svc", 3)
        assert restored.query("dc-east/host-01/svc") == 5
        assert three_level_counter.query("dc-east/host-01/svc") == 8

    def test_state_returns_copy(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc", 5)
        state = three_level_counter.get_state()
        state.counts[("dc-east",)] = 999
        assert three_level_counter.query("dc-east") == 5


class TestConcurrency:
    def test_concurrent_increments_same_path(self, three_level_counter):
        num_threads = 20
        increments_per_thread = 100
        path = "dc-east/host-01/svc"

        def worker():
            for _ in range(increments_per_thread):
                three_level_counter.increment(path, 1)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * increments_per_thread
        assert three_level_counter.query(path) == expected
        assert three_level_counter.query("dc-east/host-01") == expected
        assert three_level_counter.query("dc-east") == expected

    def test_concurrent_increments_different_paths(self, three_level_counter):
        paths = [f"dc-{i}/host-{i}/svc-{i}" for i in range(10)]
        num_threads = 10
        increments_per_thread = 50

        def worker(thread_idx):
            for i in range(increments_per_thread):
                path = paths[thread_idx % len(paths)]
                three_level_counter.increment(path, 1)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total = sum(three_level_counter.query(p) for p in paths)
        assert total == num_threads * increments_per_thread
        assert three_level_counter.total() == num_threads * increments_per_thread

    def test_concurrent_merge(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)

        def fill_counter(counter, prefix, count):
            for i in range(count):
                counter.increment(f"{prefix}-dc/host-{i}/svc", 1)

        t1 = threading.Thread(target=fill_counter, args=(c1, "a", 100))
        t2 = threading.Thread(target=fill_counter, args=(c2, "b", 100))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        c1.merge(c2)
        assert c1.total() == 200


class TestEdgeCases:
    def test_empty_counter_all_queries_zero(self, three_level_counter):
        assert three_level_counter.query("any/path/here") == 0
        assert three_level_counter.query("dc-east") == 0
        assert three_level_counter.query("a/b") == 0
        assert three_level_counter.total() == 0
        assert three_level_counter.all_paths() == []

    def test_mixed_case_paths(self, three_level_counter):
        three_level_counter.increment("DC-East/Host-01/Svc", 5)
        assert three_level_counter.query("DC-East/Host-01/Svc") == 5
        assert three_level_counter.query("dc-east/host-01/svc") == 0
        assert three_level_counter.query("DC-East") == 5

    def test_special_characters_in_path(self, three_level_counter):
        path = "dc-east.1/host-01_02/service-name.v1"
        three_level_counter.increment(path, 42)
        assert three_level_counter.query(path) == 42
        assert three_level_counter.query("dc-east.1") == 42

    def test_large_count_values(self, three_level_counter):
        large = 10**9
        three_level_counter.increment("dc-east/host-01/svc", large)
        three_level_counter.increment("dc-east/host-01/svc", large)
        assert three_level_counter.query("dc-east/host-01/svc") == 2 * large

    def test_multiple_schemas_independent(self):
        c1 = MultiDimCounter(levels=["a", "b", "c"])
        c2 = MultiDimCounter(levels=["x", "y"])
        c1.increment("a1/b1/c1", 10)
        c2.increment("x1/y1", 20)
        assert c1.query("a1/b1/c1") == 10
        assert c2.query("x1/y1") == 20
        assert c1.total() == 10
        assert c2.total() == 20


class TestCounterState:
    def test_counter_state_total(self, three_level_schema):
        counter = MultiDimCounter(schema=three_level_schema)
        counter.increment("dc-east/h1/s1", 3)
        counter.increment("dc-west/h2/s2", 7)
        state = counter.get_state()
        assert state.total() == 10

    def test_counter_state_empty_total_zero(self, three_level_schema):
        counter = MultiDimCounter(schema=three_level_schema)
        state = counter.get_state()
        assert state.total() == 0


class TestClampingConsistency:
    def test_excess_decrement_across_siblings_preserves_parent(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 10)
        three_level_counter.increment("dc-east/host-01/svc-b", 5)
        three_level_counter.decrement("dc-east/host-01/svc-a", 12)
        assert three_level_counter.query("dc-east/host-01/svc-a") == 0
        assert three_level_counter.query("dc-east/host-01/svc-b") == 5
        assert three_level_counter.query("dc-east/host-01") == 5
        assert three_level_counter.query("dc-east") == 5
        assert three_level_counter.total() == 5

    def test_excess_decrement_multiple_siblings(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 3)
        three_level_counter.increment("dc-east/host-01/svc-b", 4)
        three_level_counter.increment("dc-east/host-01/svc-c", 5)
        three_level_counter.decrement("dc-east/host-01/svc-b", 10)
        assert three_level_counter.query("dc-east/host-01/svc-a") == 3
        assert three_level_counter.query("dc-east/host-01/svc-b") == 0
        assert three_level_counter.query("dc-east/host-01/svc-c") == 5
        assert three_level_counter.query("dc-east/host-01") == 8
        assert three_level_counter.query("dc-east") == 8
        assert three_level_counter.total() == 8

    def test_negative_increment_clamp_propagates_actual_delta(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 7)
        three_level_counter.increment("dc-east/host-01/svc-b", 6)
        three_level_counter.increment("dc-east/host-01/svc-a", -20)
        assert three_level_counter.query("dc-east/host-01/svc-a") == 0
        assert three_level_counter.query("dc-east/host-01/svc-b") == 6
        assert three_level_counter.query("dc-east/host-01") == 6
        assert three_level_counter.query("dc-east") == 6

    def test_parent_equals_sum_of_children_after_clamp(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 10)
        three_level_counter.increment("dc-east/host-01/svc-b", 10)
        three_level_counter.increment("dc-east/host-01/svc-c", 10)
        three_level_counter.decrement("dc-east/host-01/svc-a", 15)
        children = three_level_counter.query_children("dc-east/host-01")
        parent_count = three_level_counter.query("dc-east/host-01")
        assert sum(children.values()) == parent_count
        assert parent_count == 20

    def test_ancestors_all_consistent_after_clamp(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 20)
        three_level_counter.increment("dc-east/host-02/svc-b", 30)
        three_level_counter.increment("dc-west/host-03/svc-c", 40)
        three_level_counter.decrement("dc-east/host-01/svc-a", 50)
        h1_children = three_level_counter.query_children("dc-east/host-01")
        assert three_level_counter.query("dc-east/host-01") == sum(h1_children.values())
        dc_children = three_level_counter.query_children("dc-east")
        assert three_level_counter.query("dc-east") == sum(dc_children.values())
        top_children = three_level_counter.query_children()
        assert three_level_counter.total() == sum(top_children.values())
        assert three_level_counter.total() == 70

    def test_consecutive_excess_decrements(self, three_level_counter):
        three_level_counter.increment("dc-east/host-01/svc-a", 10)
        three_level_counter.increment("dc-east/host-01/svc-b", 10)
        three_level_counter.decrement("dc-east/host-01/svc-a", 15)
        three_level_counter.decrement("dc-east/host-01/svc-b", 15)
        assert three_level_counter.query("dc-east/host-01/svc-a") == 0
        assert three_level_counter.query("dc-east/host-01/svc-b") == 0
        assert three_level_counter.query("dc-east/host-01") == 0
        assert three_level_counter.query("dc-east") == 0
        assert three_level_counter.total() == 0

    def test_clamp_on_merge_result(self, three_level_schema):
        c1 = MultiDimCounter(schema=three_level_schema)
        c2 = MultiDimCounter(schema=three_level_schema)
        c1.increment("dc-east/host-01/svc-a", 8)
        c1.increment("dc-east/host-01/svc-b", 4)
        c2.merge(c1)
        c2.decrement("dc-east/host-01/svc-a", 20)
        assert c2.query("dc-east/host-01/svc-a") == 0
        assert c2.query("dc-east/host-01/svc-b") == 4
        assert c2.query("dc-east/host-01") == 4
        assert c2.query("dc-east") == 4

