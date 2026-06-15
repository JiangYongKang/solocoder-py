from __future__ import annotations

import math
import pytest

from solocoder_py.cardinality import (
    HyperLogLog,
    MemoryDataSource,
    calculate_num_registers,
    create_data_source_with_duplicates,
    create_overlapping_data_sources,
    generate_random_integers,
    generate_random_strings,
)


class TestCalculateNumRegisters:
    def test_calculate_num_registers_basic(self):
        m = calculate_num_registers(0.01)
        assert m > 0
        assert (m & (m - 1)) == 0

    def test_calculate_num_registers_higher_precision_more_registers(self):
        m1 = calculate_num_registers(0.05)
        m2 = calculate_num_registers(0.01)
        assert m2 >= m1

    def test_calculate_num_registers_1_percent(self):
        m = calculate_num_registers(0.01)
        se = 1.04 / math.sqrt(m)
        assert se <= 0.01

    def test_calculate_num_registers_5_percent(self):
        m = calculate_num_registers(0.05)
        se = 1.04 / math.sqrt(m)
        assert se <= 0.05

    def test_calculate_num_registers_invalid_zero(self):
        with pytest.raises(ValueError, match="standard_error must be between 0 and 1"):
            calculate_num_registers(0.0)

    def test_calculate_num_registers_invalid_negative(self):
        with pytest.raises(ValueError, match="standard_error must be between 0 and 1"):
            calculate_num_registers(-0.01)

    def test_calculate_num_registers_invalid_greater_than_one(self):
        with pytest.raises(ValueError, match="standard_error must be between 0 and 1"):
            calculate_num_registers(1.5)


class TestHyperLogLogInit:
    def test_init_with_standard_error(self):
        hll = HyperLogLog(standard_error=0.02)
        assert hll.num_registers > 0
        assert (hll.num_registers & (hll.num_registers - 1)) == 0
        assert hll.standard_error <= 0.02

    def test_init_with_num_registers(self):
        hll = HyperLogLog(num_registers=1024)
        assert hll.num_registers == 1024
        assert hll.p == 10

    def test_init_no_params_raises(self):
        with pytest.raises(ValueError, match="Exactly one of standard_error or num_registers must be provided"):
            HyperLogLog()

    def test_init_both_params_raises(self):
        with pytest.raises(ValueError, match="Exactly one of standard_error or num_registers must be provided"):
            HyperLogLog(standard_error=0.01, num_registers=1024)

    def test_init_num_registers_not_power_of_two(self):
        with pytest.raises(ValueError, match="num_registers must be a positive power of 2"):
            HyperLogLog(num_registers=1000)

    def test_init_num_registers_too_small(self):
        with pytest.raises(ValueError, match="num_registers must be at least 16"):
            HyperLogLog(num_registers=8)

    def test_init_num_registers_zero(self):
        with pytest.raises(ValueError, match="num_registers must be a positive power of 2"):
            HyperLogLog(num_registers=0)

    def test_init_standard_error_valid_range(self):
        for se in [0.005, 0.01, 0.02, 0.03, 0.05]:
            hll = HyperLogLog(standard_error=se)
            assert hll.standard_error <= se

    def test_init_p_minimum(self):
        hll = HyperLogLog(num_registers=16)
        assert hll.p == 4

    def test_init_p_maximum(self):
        hll = HyperLogLog(num_registers=65536)
        assert hll.p == 16


class TestHyperLogLogBasicOperations:
    def test_add_single_string(self):
        hll = HyperLogLog(standard_error=0.02)
        hll.add("hello")
        card = hll.cardinality()
        assert card >= 0

    def test_add_single_integer(self):
        hll = HyperLogLog(standard_error=0.02)
        hll.add(42)
        card = hll.cardinality()
        assert card >= 0

    def test_add_bytes(self):
        hll = HyperLogLog(standard_error=0.02)
        hll.add(b"test_bytes")
        card = hll.cardinality()
        assert card >= 0

    def test_add_many(self):
        hll = HyperLogLog(standard_error=0.02)
        elements = [f"item_{i}" for i in range(100)]
        hll.add_many(elements)
        card = hll.cardinality()
        assert card > 0

    def test_len_equals_cardinality(self):
        hll = HyperLogLog(standard_error=0.02)
        hll.add("a")
        hll.add("b")
        assert len(hll) == hll.cardinality()

    def test_duplicate_elements_do_not_increase(self):
        hll = HyperLogLog(num_registers=16384)
        for _ in range(1000):
            hll.add("same_element")
        card = hll.cardinality()
        assert abs(card - 1) <= 5

    def test_cardinality_accuracy_small_set(self):
        hll = HyperLogLog(num_registers=4096)
        n = 100
        items = [f"unique_{i}" for i in range(n)]
        hll.add_many(items)
        estimated = hll.cardinality()
        error = abs(estimated - n) / n
        assert error < 0.15

    def test_cardinality_accuracy_medium_set(self):
        hll = HyperLogLog(num_registers=16384)
        n = 10000
        items = generate_random_strings(n, seed=42)
        hll.add_many(items)
        estimated = hll.cardinality()
        error = abs(estimated - n) / n
        assert error < 0.10

    def test_cardinality_accuracy_with_high_precision(self):
        hll = HyperLogLog(standard_error=0.01)
        n = 50000
        items = generate_random_strings(n, seed=123)
        hll.add_many(items)
        estimated = hll.cardinality()
        error = abs(estimated - n) / n
        assert error < 0.05

    def test_clear(self):
        hll = HyperLogLog(standard_error=0.02)
        hll.add("x")
        hll.add("y")
        assert hll.cardinality() > 0
        hll.clear()
        assert hll.cardinality() == 0

    def test_clone(self):
        hll = HyperLogLog(standard_error=0.02)
        hll.add("a")
        hll.add("b")
        cloned = hll.clone()
        assert cloned.cardinality() == hll.cardinality()
        cloned.add("c")
        assert cloned.cardinality() > hll.cardinality()

    def test_repr(self):
        hll = HyperLogLog(num_registers=1024)
        r = repr(hll)
        assert "HyperLogLog" in r
        assert "m=1024" in r
        assert "p=10" in r


class TestHyperLogLogBoundary:
    def test_empty_cardinality(self):
        hll = HyperLogLog(standard_error=0.02)
        assert hll.cardinality() == 0

    def test_single_element(self):
        hll = HyperLogLog(num_registers=16384)
        hll.add("only_one")
        card = hll.cardinality()
        assert abs(card - 1) <= 5

    def test_two_elements(self):
        hll = HyperLogLog(num_registers=16384)
        hll.add("first")
        hll.add("second")
        card = hll.cardinality()
        assert abs(card - 2) <= 6

    def test_many_duplicates(self):
        hll = HyperLogLog(num_registers=4096)
        unique = 100
        for i in range(unique):
            for _ in range(1000):
                hll.add(f"dup_{i}")
        estimated = hll.cardinality()
        error = abs(estimated - unique) / unique
        assert error < 0.20

    def test_integers(self):
        hll = HyperLogLog(num_registers=4096)
        n = 5000
        ints = generate_random_integers(n, seed=99)
        hll.add_many(ints)
        exact = len(set(ints))
        estimated = hll.cardinality()
        error = abs(estimated - exact) / exact
        assert error < 0.10

    def test_mixed_types(self):
        hll = HyperLogLog(num_registers=4096)
        items = ["string", 42, 3.14, True, b"bytes"]
        hll.add_many(items)
        card = hll.cardinality()
        assert card > 0


class TestHyperLogLogUnion:
    def test_union_basic(self):
        hll1 = HyperLogLog(num_registers=4096)
        hll2 = HyperLogLog(num_registers=4096)
        hll1.add("a")
        hll1.add("b")
        hll2.add("c")
        hll2.add("d")
        union = hll1.union(hll2)
        assert union.num_registers == 4096
        assert union.cardinality() > 0

    def test_union_operator(self):
        hll1 = HyperLogLog(num_registers=4096)
        hll2 = HyperLogLog(num_registers=4096)
        hll1.add("x")
        hll2.add("y")
        union = hll1 | hll2
        assert union.cardinality() > 0

    def test_union_idempotent(self):
        hll = HyperLogLog(num_registers=4096)
        items = [f"id_{i}" for i in range(100)]
        hll.add_many(items)
        union = hll.union(hll)
        assert abs(union.cardinality() - hll.cardinality()) <= hll.cardinality() * 0.05

    def test_union_commutative(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        items1 = generate_random_strings(500, seed=1)
        items2 = generate_random_strings(500, seed=2)
        hll1.add_many(items1)
        hll2.add_many(items2)
        u1 = (hll1 | hll2).cardinality()
        u2 = (hll2 | hll1).cardinality()
        assert abs(u1 - u2) <= max(u1, u2) * 0.02

    def test_union_accuracy_disjoint(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        items1 = [f"A_{i}" for i in range(1000)]
        items2 = [f"B_{i}" for i in range(1000)]
        hll1.add_many(items1)
        hll2.add_many(items2)
        union = hll1 | hll2
        exact = 2000
        estimated = union.cardinality()
        error = abs(estimated - exact) / exact
        assert error < 0.10

    def test_union_accuracy_overlapping(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        shared = [f"shared_{i}" for i in range(500)]
        only1 = [f"only1_{i}" for i in range(500)]
        only2 = [f"only2_{i}" for i in range(500)]
        hll1.add_many(shared + only1)
        hll2.add_many(shared + only2)
        union = hll1 | hll2
        exact = 1500
        estimated = union.cardinality()
        error = abs(estimated - exact) / exact
        assert error < 0.10

    def test_union_incompatible_precision_raises(self):
        hll1 = HyperLogLog(num_registers=1024)
        hll2 = HyperLogLog(num_registers=4096)
        with pytest.raises(ValueError, match="same precision"):
            hll1.union(hll2)

    def test_union_operator_incompatible_raises(self):
        hll1 = HyperLogLog(num_registers=1024)
        hll2 = HyperLogLog(num_registers=2048)
        with pytest.raises(ValueError, match="same precision"):
            _ = hll1 | hll2


class TestHyperLogLogIntersection:
    def test_intersection_basic(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        hll1.add("a")
        hll1.add("b")
        hll1.add("common")
        hll2.add("c")
        hll2.add("common")
        inter_card = hll1.intersection_cardinality(hll2)
        assert inter_card >= 0

    def test_intersection_disjoint(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        hll1.add("only_a_1")
        hll1.add("only_a_2")
        hll2.add("only_b_1")
        hll2.add("only_b_2")
        inter_card = hll1.intersection_cardinality(hll2)
        assert inter_card >= 0

    def test_intersection_fully_overlapping(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        items = [f"item_{i}" for i in range(500)]
        hll1.add_many(items)
        hll2.add_many(items)
        inter_card = hll1.intersection_cardinality(hll2)
        exact = 500
        error = abs(inter_card - exact) / exact
        assert error < 0.25

    def test_intersection_partial_overlap(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        shared_count = 500
        only_count = 300
        shared = [f"s_{i}" for i in range(shared_count)]
        only1 = [f"o1_{i}" for i in range(only_count)]
        only2 = [f"o2_{i}" for i in range(only_count)]
        hll1.add_many(shared + only1)
        hll2.add_many(shared + only2)
        inter_card = hll1.intersection_cardinality(hll2)
        error = abs(inter_card - shared_count) / shared_count
        assert error < 0.30

    def test_intersection_negative_fallback_to_zero(self):
        hll1 = HyperLogLog(num_registers=16384)
        hll2 = HyperLogLog(num_registers=16384)
        for i in range(10000):
            hll1.add(f"exclusive_a_{i}")
        for j in range(10000):
            hll2.add(f"exclusive_b_{j}")
        result = hll1.intersection_cardinality(hll2)
        assert result >= 0
        assert result < 1000

    def test_intersection_incompatible_raises(self):
        hll1 = HyperLogLog(num_registers=1024)
        hll2 = HyperLogLog(num_registers=4096)
        with pytest.raises(ValueError, match="same precision"):
            hll1.intersection_cardinality(hll2)

    def test_is_compatible_true(self):
        hll1 = HyperLogLog(num_registers=4096)
        hll2 = HyperLogLog(num_registers=4096)
        assert hll1.is_compatible(hll2)

    def test_is_compatible_false(self):
        hll1 = HyperLogLog(num_registers=1024)
        hll2 = HyperLogLog(num_registers=2048)
        assert not hll1.is_compatible(hll2)

    def test_is_compatible_wrong_type(self):
        hll = HyperLogLog(num_registers=1024)
        assert not hll.is_compatible("not an hll")
        assert not hll.is_compatible(None)
        assert not hll.is_compatible(42)


class TestDifferentPrecisions:
    def test_precision_1_percent(self):
        hll = HyperLogLog(standard_error=0.01)
        n = 100000
        items = generate_random_strings(n, seed=100)
        hll.add_many(items)
        estimated = hll.cardinality()
        error = abs(estimated - n) / n
        assert error < 0.05

    def test_precision_2_percent(self):
        hll = HyperLogLog(standard_error=0.02)
        n = 50000
        items = generate_random_strings(n, seed=200)
        hll.add_many(items)
        estimated = hll.cardinality()
        error = abs(estimated - n) / n
        assert error < 0.10

    def test_precision_5_percent(self):
        hll = HyperLogLog(standard_error=0.05)
        n = 10000
        items = generate_random_strings(n, seed=300)
        hll.add_many(items)
        estimated = hll.cardinality()
        error = abs(estimated - n) / n
        assert error < 0.20

    def test_independent_instances_different_precision(self):
        hll_low = HyperLogLog(standard_error=0.05)
        hll_high = HyperLogLog(standard_error=0.01)
        items = generate_random_strings(5000, seed=42)
        hll_low.add_many(items)
        hll_high.add_many(items)
        assert hll_low.num_registers < hll_high.num_registers
        assert hll_low.standard_error > hll_high.standard_error


class TestMemoryDataSource:
    def test_create_and_add(self):
        ds = MemoryDataSource(name="test")
        ds.add("item1")
        ds.add("item2")
        assert len(ds) == 2

    def test_add_many(self):
        ds = MemoryDataSource(name="test")
        items = [1, 2, 3, 4, 5]
        ds.add_many(items)
        assert len(ds) == 5

    def test_items(self):
        ds = MemoryDataSource(name="test")
        ds.add("a")
        ds.add("b")
        result = ds.items()
        assert result == ["a", "b"]

    def test_iteration(self):
        ds = MemoryDataSource(name="test")
        items = ["x", "y", "z"]
        ds.add_many(items)
        collected = []
        for item in ds:
            collected.append(item)
        assert collected == items

    def test_exact_cardinality(self):
        ds = MemoryDataSource(name="test")
        ds.add("dup")
        ds.add("dup")
        ds.add("unique")
        assert ds.exact_cardinality() == 2

    def test_feed_to_hll(self):
        ds = MemoryDataSource(name="test")
        items = [f"elem_{i}" for i in range(500)]
        ds.add_many(items)
        hll = HyperLogLog(num_registers=4096)
        ds.feed_to(hll)
        estimated = hll.cardinality()
        error = abs(estimated - 500) / 500
        assert error < 0.15

    def test_sample(self):
        ds = MemoryDataSource(name="test")
        items = list(range(100))
        ds.add_many(items)
        sample = ds.sample(10)
        assert len(sample) == 10
        for item in sample:
            assert item in items

    def test_sample_more_than_available(self):
        ds = MemoryDataSource(name="test")
        ds.add_many([1, 2, 3])
        sample = ds.sample(10)
        assert len(sample) == 3

    def test_clear(self):
        ds = MemoryDataSource(name="test")
        ds.add("x")
        ds.clear()
        assert len(ds) == 0


class TestDataSourceFactories:
    def test_generate_random_strings(self):
        strings = generate_random_strings(100, length=20, seed=42)
        assert len(strings) == 100
        for s in strings:
            assert len(s) == 20

    def test_generate_random_integers(self):
        ints = generate_random_integers(50, low=1, high=100, seed=7)
        assert len(ints) == 50
        for n in ints:
            assert 1 <= n <= 100

    def test_create_with_duplicates(self):
        ds = create_data_source_with_duplicates("dup_test", unique_count=100, duplicate_factor=5, seed=42)
        assert ds.exact_cardinality() == 100
        assert len(ds) >= 100

    def test_create_overlapping(self):
        ds_a, ds_b = create_overlapping_data_sources(
            "A", "B", unique_a=200, unique_b=250, overlap=100, seed=42
        )
        items_a = set(ds_a.items())
        items_b = set(ds_b.items())
        assert len(items_a) == 200
        assert len(items_b) == 250
        assert len(items_a & items_b) == 100

    def test_create_overlapping_invalid(self):
        with pytest.raises(ValueError, match="overlap cannot exceed"):
            create_overlapping_data_sources("A", "B", unique_a=50, unique_b=60, overlap=100)


class TestIntegrationWithDataSource:
    def test_full_workflow_disjoint_sets(self):
        ds_a, ds_b = create_overlapping_data_sources(
            "A", "B", unique_a=1000, unique_b=1000, overlap=0, seed=123
        )
        hll_a = HyperLogLog(num_registers=16384)
        hll_b = HyperLogLog(num_registers=16384)
        ds_a.feed_to(hll_a)
        ds_b.feed_to(hll_b)
        union = hll_a | hll_b
        exact_union = ds_a.exact_cardinality() + ds_b.exact_cardinality()
        union_error = abs(union.cardinality() - exact_union) / exact_union
        assert union_error < 0.10

    def test_full_workflow_overlapping_sets(self):
        overlap = 500
        ds_a, ds_b = create_overlapping_data_sources(
            "A", "B", unique_a=1000, unique_b=1200, overlap=overlap, seed=456
        )
        hll_a = HyperLogLog(num_registers=16384)
        hll_b = HyperLogLog(num_registers=16384)
        ds_a.feed_to(hll_a)
        ds_b.feed_to(hll_b)
        inter_est = hll_a.intersection_cardinality(hll_b)
        error = abs(inter_est - overlap) / overlap
        assert error < 0.30
