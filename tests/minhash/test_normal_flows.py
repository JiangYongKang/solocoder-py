from __future__ import annotations

import pytest

from solocoder_py.minhash import MinHash, jaccard_similarity


class TestMinHashBasicOperations:
    def test_init_default_params(self):
        mh = MinHash()
        assert mh.h == 128
        assert mh.num_hash_functions == 128
        assert len(mh) == 128
        assert mh._is_empty()

    def test_init_with_custom_params(self):
        mh = MinHash(num_hash_functions=64, seed=123)
        assert mh.h == 64
        assert mh.num_hash_functions == 64
        assert mh._is_empty()

    def test_init_with_elements(self):
        elements = ["a", "b", "c"]
        mh = MinHash(num_hash_functions=64, elements=elements)
        assert all(sig < 0xFFFFFFFFFFFFFFFF for sig in mh.signature)
        assert not mh._is_empty()

    def test_signature_length(self):
        for h in [16, 64, 128, 256]:
            mh = MinHash(num_hash_functions=h)
            assert len(mh.signature) == h

    def test_add_single_element(self):
        mh = MinHash(num_hash_functions=64)
        mh.add("test_element")
        for sig in mh.signature:
            assert sig < 0xFFFFFFFFFFFFFFFF
        assert not mh._is_empty()

    def test_add_multiple_elements(self):
        mh = MinHash(num_hash_functions=64)
        elements = [f"elem_{i}" for i in range(50)]
        for elem in elements:
            mh.add(elem)
        assert not mh._is_empty()
        sig_after = mh.signature
        mh.add("new_elem")
        assert any(
            mh.signature[i] < sig_after[i] for i in range(64)
        ) or all(
            mh.signature[i] == sig_after[i] for i in range(64)
        )

    def test_add_duplicate_element(self):
        mh = MinHash(num_hash_functions=64)
        mh.add("duplicate")
        sig_after_first = mh.signature
        mh.add("duplicate")
        assert mh.signature == sig_after_first

    def test_add_many(self):
        mh = MinHash(num_hash_functions=64)
        elements = [f"elem_{i}" for i in range(30)]
        mh.add_many(elements)
        assert not mh._is_empty()

    def test_update_method(self):
        mh = MinHash(num_hash_functions=64)
        elements = [f"elem_{i}" for i in range(20)]
        mh.update(elements)
        assert not mh._is_empty()

    def test_from_set_classmethod(self):
        elements = {f"elem_{i}" for i in range(25)}
        mh = MinHash.from_set(elements, num_hash_functions=64)
        assert mh.h == 64
        assert not mh._is_empty()

    def test_signature_property_returns_copy(self):
        mh = MinHash(num_hash_functions=64)
        mh.add("test")
        sig1 = mh.signature
        sig2 = mh.signature
        sig1[0] = 999
        assert sig2[0] != 999


class TestJaccardEstimation:
    def test_identical_sets_jaccard_equals_one(self):
        elements = {f"item_{i}" for i in range(100)}
        mh1 = MinHash.from_set(elements, num_hash_functions=256, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=256, seed=42)
        assert mh1.jaccard(mh2) == pytest.approx(1.0)

    def test_disjoint_sets_jaccard_near_zero(self):
        set_a = {f"a_{i}" for i in range(100)}
        set_b = {f"b_{i}" for i in range(100)}
        mh1 = MinHash.from_set(set_a, num_hash_functions=256, seed=42)
        mh2 = MinHash.from_set(set_b, num_hash_functions=256, seed=42)
        estimated = mh1.jaccard(mh2)
        assert estimated < 0.1

    def test_partial_overlap_estimation_within_error_bounds(self):
        set_a = {f"item_{i}" for i in range(200)}
        overlap = {f"item_{i}" for i in range(50, 150)}
        set_b = {f"item_{i}" for i in range(100, 300)}
        true_jaccard = jaccard_similarity(set_a, set_b)
        mh1 = MinHash.from_set(set_a, num_hash_functions=256, seed=42)
        mh2 = MinHash.from_set(set_b, num_hash_functions=256, seed=42)
        estimated = mh1.jaccard(mh2)
        assert abs(estimated - true_jaccard) < 0.1

    def test_larger_h_gives_better_precision(self):
        set_a = {f"x_{i}" for i in range(300)}
        set_b = {f"x_{i}" for i in range(100, 400)}
        true_jaccard = jaccard_similarity(set_a, set_b)
        errors = {}
        for h in [16, 64, 256]:
            mh1 = MinHash.from_set(set_a, num_hash_functions=h, seed=42)
            mh2 = MinHash.from_set(set_b, num_hash_functions=h, seed=42)
            estimated = mh1.jaccard(mh2)
            errors[h] = abs(estimated - true_jaccard)
        assert errors[256] <= errors[64]
        assert errors[64] <= errors[16]

    def test_incremental_add_vs_one_shot(self):
        elements = [f"data_{i}" for i in range(150)]
        mh_incremental = MinHash(num_hash_functions=128, seed=42)
        for elem in elements:
            mh_incremental.add(elem)
        mh_oneshot = MinHash.from_set(elements, num_hash_functions=128, seed=42)
        assert mh_incremental.signature == mh_oneshot.signature
        assert mh_incremental.jaccard(mh_oneshot) == pytest.approx(1.0)

    def test_different_seeds_produce_different_signatures(self):
        elements = [f"elem_{i}" for i in range(50)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=123)
        assert mh1.signature != mh2.signature

    def test_same_seed_produce_identical_signatures(self):
        elements = [f"elem_{i}" for i in range(50)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        assert mh1.signature == mh2.signature

    def test_hash_functions_are_independent(self):
        mh = MinHash(num_hash_functions=128, seed=42)
        mh.add("test_element")
        sig = mh.signature
        unique_values = len(set(sig))
        assert unique_values > 1


class TestMergeOperations:
    def test_merge_basic(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("a")
        mh1.add("b")
        mh2.add("c")
        mh2.add("d")
        merged = mh1.merge(mh2)
        assert merged.h == 64
        for i in range(64):
            assert merged.signature[i] == min(
                mh1.signature[i], mh2.signature[i]
            )

    def test_merge_operator(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("x")
        mh2.add("y")
        merged = mh1 | mh2
        assert merged.h == 64
        for i in range(64):
            assert merged.signature[i] == min(
                mh1.signature[i], mh2.signature[i]
            )

    def test_in_place_merge(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("p")
        mh2.add("q")
        sig1_before = mh1.signature
        sig2 = mh2.signature
        mh1 |= mh2
        for i in range(64):
            assert mh1.signature[i] == min(sig1_before[i], sig2[i])

    def test_merge_idempotent(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add("a")
        mh.add("b")
        merged = mh.merge(mh)
        assert merged.signature == mh.signature

    def test_merge_commutative(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("a")
        mh2.add("b")
        m1 = mh1.merge(mh2)
        m2 = mh2.merge(mh1)
        assert m1.signature == m2.signature

    def test_merge_with_identical_sets(self):
        elements = [f"elem_{i}" for i in range(50)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        merged = mh1.merge(mh2)
        assert merged.signature == mh1.signature

    def test_merge_preserves_compatibility(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("a")
        mh2.add("b")
        merged = mh1.merge(mh2)
        assert merged.is_compatible(mh1)
        assert merged.is_compatible(mh2)

    def test_merge_correctly_takes_min(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        for i in range(30):
            mh1.add(f"mh1_{i}")
        for i in range(50):
            mh2.add(f"mh2_{i}")
        merged = mh1.merge(mh2)
        for i in range(64):
            assert merged.signature[i] == min(
                mh1.signature[i], mh2.signature[i]
            )


class TestIsCompatible:
    def test_compatible_same_h_and_seed(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        assert mh1.is_compatible(mh2)
        assert mh2.is_compatible(mh1)

    def test_incompatible_different_h(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        assert not mh1.is_compatible(mh2)

    def test_incompatible_different_seed(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=123)
        assert not mh1.is_compatible(mh2)

    def test_incompatible_different_type(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        assert not mh.is_compatible("not a minhash")

    def test_compatible_seeds_with_same_modulus(self):
        max_seed = 2**32 - 1
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42 + max_seed)
        assert mh1.is_compatible(mh2)
        assert mh2.is_compatible(mh1)

    def test_same_modulus_seeds_produce_same_signature(self):
        max_seed = 2**32 - 1
        elements = [f"elem_{i}" for i in range(30)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=42 + max_seed)
        assert mh1.signature == mh2.signature

    def test_same_modulus_seeds_jaccard_equals_one(self):
        max_seed = 2**32 - 1
        elements = [f"item_{i}" for i in range(50)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=42 + max_seed)
        assert mh1.jaccard(mh2) == pytest.approx(1.0)

    def test_negative_seed_normalized(self):
        max_seed = 2**32 - 1
        elements = [f"elem_{i}" for i in range(20)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=-100)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=max_seed - 100)
        assert mh1.is_compatible(mh2)
        assert mh1.signature == mh2.signature

    def test_seed_plus_max_seed_is_compatible(self):
        max_seed = 2**32 - 1
        elements = [f"elem_{i}" for i in range(20)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=12345)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=12345 + max_seed)
        assert mh1.is_compatible(mh2)
        assert mh1.signature == mh2.signature

    def test_large_positive_seed_normalized(self):
        max_seed = 2**32 - 1
        elements = [f"elem_{i}" for i in range(20)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=42 + 2 * max_seed)
        assert mh1.is_compatible(mh2)
        assert mh1.signature == mh2.signature


class TestEquality:
    def test_equal_same_signature(self):
        elements = [f"elem_{i}" for i in range(50)]
        mh1 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        mh2 = MinHash.from_set(elements, num_hash_functions=64, seed=42)
        assert mh1 == mh2

    def test_not_equal_different_signature(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("a")
        mh2.add("b")
        assert mh1 != mh2

    def test_not_equal_different_h(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        assert mh1 != mh2

    def test_not_equal_different_type(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        assert mh != "not a minhash"


class TestRepr:
    def test_repr_empty(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        r = repr(mh)
        assert "MinHash" in r
        assert "num_hash_functions=64" in r
        assert "seed=42" in r

    def test_repr_with_elements(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add("test")
        r = repr(mh)
        assert "MinHash" in r
        assert "num_hash_functions=64" in r
        assert "seed=42" in r
