from __future__ import annotations

import pytest

from solocoder_py.minhash import MinHash, jaccard_similarity


class TestEmptySet:
    def test_empty_set_signature(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        assert mh._is_empty()
        for sig in mh.signature:
            assert sig == 0xFFFFFFFFFFFFFFFF

    def test_two_empty_sets_jaccard_is_one(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        assert mh1.jaccard(mh2) == pytest.approx(1.0)

    def test_empty_and_nonempty_jaccard(self):
        mh_empty = MinHash(num_hash_functions=64, seed=42)
        mh_nonempty = MinHash(num_hash_functions=64, seed=42)
        mh_nonempty.add("element")
        estimated = mh_empty.jaccard(mh_nonempty)
        assert 0 <= estimated <= 0.1

    def test_empty_set_with_elements_init(self):
        mh = MinHash(num_hash_functions=64, seed=42, elements=[])
        assert mh._is_empty()
        for sig in mh.signature:
            assert sig == 0xFFFFFFFFFFFFFFFF

    def test_from_set_with_empty_set(self):
        mh = MinHash.from_set(set(), num_hash_functions=64, seed=42)
        assert mh._is_empty()
        for sig in mh.signature:
            assert sig == 0xFFFFFFFFFFFFFFFF


class TestSingleElement:
    def test_single_element_signature(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add("only_element")
        assert not mh._is_empty()
        for sig in mh.signature:
            assert sig < 0xFFFFFFFFFFFFFFFF

    def test_single_element_jaccard_with_itself(self):
        mh = MinHash(num_hash_functions=128, seed=42)
        mh.add("single")
        assert mh.jaccard(mh) == pytest.approx(1.0)

    def test_two_single_different_elements_jaccard(self):
        mh1 = MinHash(num_hash_functions=128, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        mh1.add("a")
        mh2.add("b")
        estimated = mh1.jaccard(mh2)
        assert estimated < 0.1

    def test_single_element_from_set(self):
        mh = MinHash.from_set({"only_one"}, num_hash_functions=64, seed=42)
        assert not mh._is_empty()
        assert all(sig < 0xFFFFFFFFFFFFFFFF for sig in mh.signature)


class TestHEqualsOne:
    def test_h_equals_one_init(self):
        mh = MinHash(num_hash_functions=1, seed=42)
        assert mh.h == 1
        assert len(mh.signature) == 1

    def test_h_equals_one_add_element(self):
        mh = MinHash(num_hash_functions=1, seed=42)
        mh.add("test")
        assert not mh._is_empty()
        assert len(mh.signature) == 1
        assert mh.signature[0] < 0xFFFFFFFFFFFFFFFF

    def test_h_equals_one_jaccard_identical(self):
        mh1 = MinHash(num_hash_functions=1, seed=42)
        mh2 = MinHash(num_hash_functions=1, seed=42)
        mh1.add("same")
        mh2.add("same")
        assert mh1.jaccard(mh2) == pytest.approx(1.0)

    def test_h_equals_one_jaccard_different(self):
        mh1 = MinHash(num_hash_functions=1, seed=42)
        mh2 = MinHash(num_hash_functions=1, seed=42)
        mh1.add("a")
        mh2.add("b")
        estimated = mh1.jaccard(mh2)
        assert estimated in [0.0, 1.0]

    def test_h_equals_one_merge(self):
        mh1 = MinHash(num_hash_functions=1, seed=42)
        mh2 = MinHash(num_hash_functions=1, seed=42)
        mh1.add("x")
        mh2.add("y")
        merged = mh1.merge(mh2)
        assert merged.h == 1
        assert merged.signature[0] == min(
            mh1.signature[0], mh2.signature[0]
        )


class TestVariousElementTypes:
    def test_string_elements(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add("hello")
        mh.add("world")
        assert not mh._is_empty()
        sig = mh.signature
        mh.add("new_string")
        assert any(
            mh.signature[i] < sig[i] for i in range(64)
        ) or all(
            mh.signature[i] == sig[i] for i in range(64)
        )

    def test_integer_elements(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add(42)
        mh.add(123)
        assert not mh._is_empty()

    def test_float_elements(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add(3.14)
        mh.add(2.718)
        assert not mh._is_empty()

    def test_boolean_elements(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add(True)
        mh.add(False)
        assert not mh._is_empty()

    def test_bytes_elements(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add(b"hello")
        mh.add(b"world")
        assert not mh._is_empty()

    def test_tuple_elements(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add((1, 2, 3))
        mh.add(("a", "b"))
        assert not mh._is_empty()

    def test_none_element(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add(None)
        assert not mh._is_empty()

    def test_frozenset_element(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add(frozenset([1, 2, 3]))
        assert not mh._is_empty()

    def test_mixed_element_types(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        mh.add("string")
        mh.add(42)
        mh.add(3.14)
        mh.add(True)
        mh.add((1, 2))
        assert not mh._is_empty()


class TestLargeScale:
    def test_large_number_of_elements(self):
        mh = MinHash(num_hash_functions=128, seed=42)
        for i in range(10000):
            mh.add(f"large_{i}")
        assert len(mh.signature) == 128
        assert not mh._is_empty()
        sig_after_10000 = mh.signature
        mh.add(f"large_10000")
        assert any(
            mh.signature[i] < sig_after_10000[i] for i in range(128)
        ) or all(
            mh.signature[i] == sig_after_10000[i] for i in range(128)
        )

    def test_large_hash_function_count(self):
        mh = MinHash(num_hash_functions=1024, seed=42)
        assert mh.h == 1024
        assert len(mh.signature) == 1024
        mh.add("test")
        assert len(mh.signature) == 1024

    def test_large_jaccard_estimation_accuracy(self):
        set_a = {f"elem_{i}" for i in range(1000)}
        set_b = {f"elem_{i}" for i in range(500, 1500)}
        true_jaccard = jaccard_similarity(set_a, set_b)
        mh1 = MinHash.from_set(set_a, num_hash_functions=512, seed=42)
        mh2 = MinHash.from_set(set_b, num_hash_functions=512, seed=42)
        estimated = mh1.jaccard(mh2)
        assert abs(estimated - true_jaccard) < 0.05


class TestMergeEdgeCases:
    def test_merge_empty_with_nonempty(self):
        mh_empty = MinHash(num_hash_functions=64, seed=42)
        mh_nonempty = MinHash(num_hash_functions=64, seed=42)
        mh_nonempty.add("data")
        merged = mh_empty.merge(mh_nonempty)
        assert merged.signature == mh_nonempty.signature

    def test_merge_empty_with_empty(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        merged = mh1.merge(mh2)
        assert merged._is_empty()
        assert all(sig == 0xFFFFFFFFFFFFFFFF for sig in merged.signature)

    def test_in_place_merge_empty_with_nonempty(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh2.add("data")
        sig2 = mh2.signature
        mh1 |= mh2
        assert mh1.signature == sig2

    def test_chain_merges(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh3 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("a")
        mh2.add("b")
        mh3.add("c")
        merged1 = mh1.merge(mh2)
        merged2 = merged1.merge(mh3)
        for i in range(64):
            assert merged2.signature[i] == min(
                mh1.signature[i], mh2.signature[i], mh3.signature[i]
            )


class TestJaccardBoundaryValues:
    def test_jaccard_between_0_and_1(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=42)
        mh1.add("x")
        mh2.add("y")
        j = mh1.jaccard(mh2)
        assert 0.0 <= j <= 1.0

    def test_complete_overlap_true_jaccard(self):
        s1 = {"a", "b", "c"}
        s2 = {"a", "b", "c"}
        assert jaccard_similarity(s1, s2) == pytest.approx(1.0)

    def test_no_overlap_true_jaccard(self):
        s1 = {"a", "b", "c"}
        s2 = {"d", "e", "f"}
        assert jaccard_similarity(s1, s2) == pytest.approx(0.0)

    def test_empty_sets_true_jaccard(self):
        s1 = set()
        s2 = set()
        assert jaccard_similarity(s1, s2) == pytest.approx(1.0)

    def test_one_empty_true_jaccard(self):
        s1 = set()
        s2 = {"a", "b"}
        assert jaccard_similarity(s1, s2) == pytest.approx(0.0)
