from __future__ import annotations

import math

import pytest

from solocoder_py.bloom_filter import (
    BloomFilter,
    CountingBloomFilter,
    calculate_optimal_k,
    calculate_optimal_m,
)


class TestOptimalParameters:
    def test_calculate_optimal_m_basic(self):
        m = calculate_optimal_m(1000, 0.01)
        assert m > 0
        assert isinstance(m, int)

    def test_calculate_optimal_m_known_value(self):
        expected_n = 1000
        target_p = 0.01
        m = calculate_optimal_m(expected_n, target_p)
        expected = math.ceil(-(expected_n * math.log(target_p)) / (math.log(2) ** 2))
        assert m == expected

    def test_calculate_optimal_m_small_p(self):
        m1 = calculate_optimal_m(1000, 0.01)
        m2 = calculate_optimal_m(1000, 0.001)
        assert m2 > m1

    def test_calculate_optimal_m_large_n(self):
        m1 = calculate_optimal_m(100, 0.01)
        m2 = calculate_optimal_m(1000, 0.01)
        assert m2 > m1

    def test_calculate_optimal_m_invalid_n_zero(self):
        with pytest.raises(ValueError, match="expected_n must be a positive integer"):
            calculate_optimal_m(0, 0.01)

    def test_calculate_optimal_m_invalid_n_negative(self):
        with pytest.raises(ValueError, match="expected_n must be a positive integer"):
            calculate_optimal_m(-1, 0.01)

    def test_calculate_optimal_m_invalid_p_zero(self):
        with pytest.raises(ValueError, match="target_p must be between 0 and 1"):
            calculate_optimal_m(100, 0.0)

    def test_calculate_optimal_m_invalid_p_one(self):
        with pytest.raises(ValueError, match="target_p must be between 0 and 1"):
            calculate_optimal_m(100, 1.0)

    def test_calculate_optimal_m_invalid_p_negative(self):
        with pytest.raises(ValueError, match="target_p must be between 0 and 1"):
            calculate_optimal_m(100, -0.01)

    def test_calculate_optimal_m_invalid_p_greater_than_one(self):
        with pytest.raises(ValueError, match="target_p must be between 0 and 1"):
            calculate_optimal_m(100, 1.5)

    def test_calculate_optimal_k_basic(self):
        k = calculate_optimal_k(1000, 9586)
        assert k > 0
        assert isinstance(k, int)

    def test_calculate_optimal_k_known_value(self):
        n = 1000
        m = calculate_optimal_m(n, 0.01)
        k = calculate_optimal_k(n, m)
        expected = round((m / n) * math.log(2))
        assert k == max(1, expected)

    def test_calculate_optimal_k_invalid_n(self):
        with pytest.raises(ValueError, match="expected_n must be a positive integer"):
            calculate_optimal_k(0, 100)

    def test_calculate_optimal_k_invalid_m(self):
        with pytest.raises(ValueError, match="m must be a positive integer"):
            calculate_optimal_k(100, 0)


class TestBloomFilterInit:
    def test_init_with_m_k(self):
        bf = BloomFilter(m=1000, k=5)
        assert bf.m == 1000
        assert bf.k == 5
        assert bf.count == 0

    def test_init_with_expected_n_target_p(self):
        bf = BloomFilter(expected_n=1000, target_p=0.01)
        expected_m = calculate_optimal_m(1000, 0.01)
        expected_k = calculate_optimal_k(1000, expected_m)
        assert bf.m == expected_m
        assert bf.k == expected_k
        assert bf.count == 0

    def test_init_no_params_raises(self):
        with pytest.raises(ValueError, match="Either \\(m, k\\) or \\(expected_n, target_p\\) must be provided"):
            BloomFilter()

    def test_init_only_m_raises(self):
        with pytest.raises(ValueError, match="Either \\(m, k\\) or \\(expected_n, target_p\\) must be provided"):
            BloomFilter(m=1000)

    def test_init_only_k_raises(self):
        with pytest.raises(ValueError, match="Either \\(m, k\\) or \\(expected_n, target_p\\) must be provided"):
            BloomFilter(k=5)

    def test_init_only_expected_n_raises(self):
        with pytest.raises(ValueError, match="Either \\(m, k\\) or \\(expected_n, target_p\\) must be provided"):
            BloomFilter(expected_n=1000)

    def test_init_only_target_p_raises(self):
        with pytest.raises(ValueError, match="Either \\(m, k\\) or \\(expected_n, target_p\\) must be provided"):
            BloomFilter(target_p=0.01)

    def test_init_invalid_m_zero(self):
        with pytest.raises(ValueError, match="m must be a positive integer"):
            BloomFilter(m=0, k=5)

    def test_init_invalid_m_negative(self):
        with pytest.raises(ValueError, match="m must be a positive integer"):
            BloomFilter(m=-1, k=5)

    def test_init_invalid_k_zero(self):
        with pytest.raises(ValueError, match="k must be a positive integer"):
            BloomFilter(m=100, k=0)

    def test_init_invalid_k_negative(self):
        with pytest.raises(ValueError, match="k must be a positive integer"):
            BloomFilter(m=100, k=-1)


class TestBloomFilterBasicOperations:
    def test_add_and_contains_string(self):
        bf = BloomFilter(m=1000, k=5)
        bf.add("hello")
        assert "hello" in bf
        assert bf.might_contain("hello")

    def test_add_and_contains_int(self):
        bf = BloomFilter(m=1000, k=5)
        bf.add(42)
        assert 42 in bf
        assert bf.might_contain(42)

    def test_add_and_contains_bytes(self):
        bf = BloomFilter(m=1000, k=5)
        bf.add(b"test")
        assert b"test" in bf

    def test_add_multiple(self):
        bf = BloomFilter(m=10000, k=7)
        elements = [f"item_{i}" for i in range(100)]
        for elem in elements:
            bf.add(elem)
        for elem in elements:
            assert elem in bf
        assert bf.count == 100

    def test_count_increments(self):
        bf = BloomFilter(m=1000, k=5)
        assert bf.count == 0
        bf.add("a")
        assert bf.count == 1
        bf.add("b")
        assert bf.count == 2
        bf.add("c")
        assert bf.count == 3

    def test_count_no_duplicate_increment(self):
        bf = BloomFilter(m=1000, k=5)
        bf.add("unique")
        first_count = bf.count
        bf.add("unique")
        assert bf.count == first_count

    def test_len_equals_count(self):
        bf = BloomFilter(m=1000, k=5)
        bf.add("a")
        bf.add("b")
        assert len(bf) == bf.count


class TestBloomFilterNoFalseNegatives:
    def test_empty_filter_contains_nothing(self):
        bf = BloomFilter(m=1000, k=5)
        for i in range(100):
            assert f"nonexistent_{i}" not in bf

    def test_added_elements_always_found(self):
        bf = BloomFilter(m=100000, k=10)
        elements = [f"definite_{i}" for i in range(1000)]
        for elem in elements:
            bf.add(elem)
        for elem in elements:
            assert elem in bf, f"Element {elem} should definitely be in filter"

    def test_no_false_negatives_with_small_filter(self):
        bf = BloomFilter(m=100, k=3)
        elements = ["x", "y", "z", "w", "v"]
        for elem in elements:
            bf.add(elem)
        for elem in elements:
            assert elem in bf


class TestBloomFilterFalsePositiveRate:
    def test_fpr_zero_when_empty(self):
        bf = BloomFilter(m=1000, k=5)
        assert bf.false_positive_rate() == 0.0

    def test_fpr_increases_with_elements(self):
        bf = BloomFilter(m=10000, k=5)
        fprs = []
        for i in range(0, 1000, 100):
            for j in range(100):
                bf.add(f"batch_{i}_{j}")
            fprs.append(bf.false_positive_rate())
        for i in range(1, len(fprs)):
            assert fprs[i] >= fprs[i - 1]

    def test_fpr_within_expected_bounds(self):
        expected_n = 1000
        target_p = 0.05
        bf = BloomFilter(expected_n=expected_n, target_p=target_p)
        for i in range(expected_n):
            bf.add(f"elem_{i}")
        actual_fpr = bf.false_positive_rate()
        assert 0 <= actual_fpr <= 1.0


class TestBloomFilterBoundary:
    def test_empty_filter_query(self):
        bf = BloomFilter(m=100, k=3)
        assert "anything" not in bf
        assert bf.count == 0
        assert bf.false_positive_rate() == 0.0

    def test_full_filter_saturation(self):
        bf = BloomFilter(m=64, k=2)
        for i in range(1000):
            bf.add(f"elem_{i}")
        assert bf.false_positive_rate() <= 1.0

    def test_single_bit_filter(self):
        bf = BloomFilter(m=1, k=1)
        bf.add("only_one_bit")
        assert "only_one_bit" in bf
        assert bf.count == 1

    def test_single_hash_function(self):
        bf = BloomFilter(m=1000, k=1)
        bf.add("single_hash")
        assert "single_hash" in bf


class TestBloomFilterUnionIntersection:
    def test_union_basic(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=1000, k=5)
        bf1.add("a")
        bf1.add("b")
        bf2.add("c")
        bf2.add("d")
        union = bf1.union(bf2)
        assert union.m == 1000
        assert union.k == 5
        assert "a" in union
        assert "b" in union
        assert "c" in union
        assert "d" in union

    def test_union_operator(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=1000, k=5)
        bf1.add("x")
        bf2.add("y")
        union = bf1 | bf2
        assert "x" in union
        assert "y" in union

    def test_union_idempotent(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf1.add("a")
        bf1.add("b")
        union = bf1.union(bf1)
        assert "a" in union
        assert "b" in union

    def test_union_commutative(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=1000, k=5)
        bf1.add("a")
        bf2.add("b")
        u1 = bf1 | bf2
        u2 = bf2 | bf1
        assert ("a" in u1) == ("a" in u2)
        assert ("b" in u1) == ("b" in u2)

    def test_intersection_basic(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=1000, k=5)
        bf1.add("a")
        bf1.add("b")
        bf1.add("common")
        bf2.add("c")
        bf2.add("common")
        inter = bf1.intersection(bf2)
        assert "common" in inter

    def test_intersection_operator(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=1000, k=5)
        bf1.add("x")
        bf1.add("shared")
        bf2.add("shared")
        bf2.add("y")
        inter = bf1 & bf2
        assert "shared" in inter

    def test_intersection_empty(self):
        bf1 = BloomFilter(m=100000, k=10)
        bf2 = BloomFilter(m=100000, k=10)
        bf1.add("only_a_in_bf1")
        bf2.add("only_b_in_bf2")
        inter = bf1 & bf2
        assert "only_a_in_bf1" not in inter
        assert "only_b_in_bf2" not in inter

    def test_union_incompatible_m(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=2000, k=5)
        with pytest.raises(ValueError, match="filters must have the same m and k"):
            bf1.union(bf2)

    def test_union_incompatible_k(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=1000, k=7)
        with pytest.raises(ValueError, match="filters must have the same m and k"):
            bf1.union(bf2)

    def test_intersection_incompatible_m(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=2000, k=5)
        with pytest.raises(ValueError, match="filters must have the same m and k"):
            bf1.intersection(bf2)

    def test_intersection_incompatible_k(self):
        bf1 = BloomFilter(m=1000, k=5)
        bf2 = BloomFilter(m=1000, k=7)
        with pytest.raises(ValueError, match="filters must have the same m and k"):
            bf1.intersection(bf2)

    def test_is_compatible_true(self):
        bf1 = BloomFilter(m=500, k=3)
        bf2 = BloomFilter(m=500, k=3)
        assert bf1.is_compatible(bf2)

    def test_is_compatible_false_m(self):
        bf1 = BloomFilter(m=500, k=3)
        bf2 = BloomFilter(m=600, k=3)
        assert not bf1.is_compatible(bf2)

    def test_is_compatible_false_k(self):
        bf1 = BloomFilter(m=500, k=3)
        bf2 = BloomFilter(m=500, k=4)
        assert not bf1.is_compatible(bf2)

    def test_is_compatible_wrong_type(self):
        bf = BloomFilter(m=500, k=3)
        assert not bf.is_compatible("not a bloom filter")


class TestBloomFilterRepr:
    def test_repr_empty(self):
        bf = BloomFilter(m=100, k=3)
        r = repr(bf)
        assert "BloomFilter" in r
        assert "m=100" in r
        assert "k=3" in r

    def test_repr_with_elements(self):
        bf = BloomFilter(m=1000, k=5)
        bf.add("test")
        r = repr(bf)
        assert "count=1" in r


class TestCountingBloomFilterInit:
    def test_init_with_m_k(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        assert cbf.m == 1000
        assert cbf.k == 5
        assert cbf.count == 0

    def test_init_with_expected_n_target_p(self):
        cbf = CountingBloomFilter(expected_n=1000, target_p=0.01)
        expected_m = calculate_optimal_m(1000, 0.01)
        expected_k = calculate_optimal_k(1000, expected_m)
        assert cbf.m == expected_m
        assert cbf.k == expected_k
        assert cbf.count == 0

    def test_init_no_params_raises(self):
        with pytest.raises(ValueError):
            CountingBloomFilter()


class TestCountingBloomFilterAdd:
    def test_add_and_contains(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        cbf.add("hello")
        assert "hello" in cbf
        assert cbf.count == 1

    def test_add_multiple(self):
        cbf = CountingBloomFilter(m=10000, k=7)
        for i in range(100):
            cbf.add(f"item_{i}")
        for i in range(100):
            assert f"item_{i}" in cbf
        assert cbf.count == 100


class TestCountingBloomFilterRemove:
    def test_remove_added_element(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        cbf.add("removable")
        assert "removable" in cbf
        assert cbf.count == 1
        cbf.remove("removable")
        assert cbf.count == 0
        assert "removable" not in cbf

    def test_remove_not_added_raises(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        with pytest.raises(ValueError, match="Cannot remove element that was not added"):
            cbf.remove("never_added")

    def test_remove_partially_not_added_raises(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        cbf.add("existing")
        with pytest.raises(ValueError, match="Cannot remove element that was not added"):
            cbf.remove("nonexistent")

    def test_add_remove_add_same_element(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        cbf.add("recycled")
        assert "recycled" in cbf
        cbf.remove("recycled")
        assert "recycled" not in cbf
        cbf.add("recycled")
        assert "recycled" in cbf
        assert cbf.count == 1

    def test_add_twice_remove_once(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        cbf.add("double")
        cbf.add("double")
        assert cbf.count == 2
        assert "double" in cbf
        cbf.remove("double")
        assert cbf.count == 1
        assert "double" in cbf

    def test_add_twice_remove_twice(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        cbf.add("double_remove")
        cbf.add("double_remove")
        cbf.remove("double_remove")
        cbf.remove("double_remove")
        assert cbf.count == 0
        assert "double_remove" not in cbf

    def test_remove_count_decrement(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        cbf.add("a")
        cbf.add("b")
        cbf.add("c")
        assert cbf.count == 3
        cbf.remove("b")
        assert cbf.count == 2
        assert "a" in cbf
        assert "b" not in cbf
        assert "c" in cbf

    def test_remove_one_does_not_affect_others(self):
        cbf = CountingBloomFilter(m=10000, k=10)
        elements = [f"elem_{i}" for i in range(50)]
        for elem in elements:
            cbf.add(elem)
        to_remove = elements[10]
        cbf.remove(to_remove)
        for i, elem in enumerate(elements):
            if i == 10:
                assert elem not in cbf
            else:
                assert elem in cbf


class TestCountingBloomFilterBoundary:
    def test_empty_remove_raises(self):
        cbf = CountingBloomFilter(m=100, k=3)
        with pytest.raises(ValueError):
            cbf.remove("nothing")

    def test_delete_after_multiple_adds_chain(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        for _ in range(5):
            cbf.add("chained")
        assert cbf.count == 5
        for _ in range(3):
            cbf.remove("chained")
        assert cbf.count == 2
        assert "chained" in cbf
        for _ in range(2):
            cbf.remove("chained")
        assert cbf.count == 0
        assert "chained" not in cbf


class TestCountingBloomFilterFPR:
    def test_fpr_zero_when_empty(self):
        cbf = CountingBloomFilter(m=1000, k=5)
        assert cbf.false_positive_rate() == 0.0

    def test_fpr_decreases_after_delete(self):
        cbf = CountingBloomFilter(expected_n=1000, target_p=0.05)
        for i in range(500):
            cbf.add(f"fpr_test_{i}")
        fpr_before = cbf.false_positive_rate()
        for i in range(250):
            cbf.remove(f"fpr_test_{i}")
        fpr_after = cbf.false_positive_rate()
        assert fpr_after <= fpr_before


class TestCountingBloomFilterUnionIntersection:
    def test_union_basic(self):
        cbf1 = CountingBloomFilter(m=1000, k=5)
        cbf2 = CountingBloomFilter(m=1000, k=5)
        cbf1.add("a")
        cbf2.add("b")
        union = cbf1.union(cbf2)
        assert "a" in union
        assert "b" in union

    def test_union_operator(self):
        cbf1 = CountingBloomFilter(m=1000, k=5)
        cbf2 = CountingBloomFilter(m=1000, k=5)
        cbf1.add("x")
        cbf2.add("y")
        union = cbf1 | cbf2
        assert "x" in union
        assert "y" in union

    def test_intersection_basic(self):
        cbf1 = CountingBloomFilter(m=1000, k=5)
        cbf2 = CountingBloomFilter(m=1000, k=5)
        cbf1.add("a")
        cbf1.add("common")
        cbf2.add("common")
        cbf2.add("b")
        inter = cbf1.intersection(cbf2)
        assert "common" in inter

    def test_intersection_operator(self):
        cbf1 = CountingBloomFilter(m=1000, k=5)
        cbf2 = CountingBloomFilter(m=1000, k=5)
        cbf1.add("shared")
        cbf2.add("shared")
        inter = cbf1 & cbf2
        assert "shared" in inter

    def test_union_incompatible(self):
        cbf1 = CountingBloomFilter(m=1000, k=5)
        cbf2 = CountingBloomFilter(m=2000, k=5)
        with pytest.raises(ValueError):
            cbf1.union(cbf2)

    def test_intersection_incompatible(self):
        cbf1 = CountingBloomFilter(m=1000, k=5)
        cbf2 = CountingBloomFilter(m=1000, k=7)
        with pytest.raises(ValueError):
            cbf1.intersection(cbf2)

    def test_is_compatible(self):
        cbf1 = CountingBloomFilter(m=500, k=3)
        cbf2 = CountingBloomFilter(m=500, k=3)
        assert cbf1.is_compatible(cbf2)
        cbf3 = CountingBloomFilter(m=500, k=4)
        assert not cbf1.is_compatible(cbf3)


class TestCountingBloomFilterRepr:
    def test_repr(self):
        cbf = CountingBloomFilter(m=100, k=3)
        r = repr(cbf)
        assert "CountingBloomFilter" in r
        assert "m=100" in r
        assert "k=3" in r
