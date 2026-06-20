from __future__ import annotations

import pytest

from solocoder_py.minhash import (
    IncompatibleSignatureError,
    InvalidConfigError,
    MinHash,
    MinHashError,
    NonHashableElementError,
)


class TestInitExceptions:
    def test_h_zero_raises_invalid_config(self):
        with pytest.raises(
            InvalidConfigError, match="num_hash_functions must be a positive integer"
        ):
            MinHash(num_hash_functions=0)

    def test_h_negative_raises_invalid_config(self):
        with pytest.raises(
            InvalidConfigError, match="num_hash_functions must be a positive integer"
        ):
            MinHash(num_hash_functions=-1)

    def test_h_negative_large_raises_invalid_config(self):
        with pytest.raises(
            InvalidConfigError, match="num_hash_functions must be a positive integer"
        ):
            MinHash(num_hash_functions=-100)

    def test_h_float_raises_invalid_config(self):
        with pytest.raises(
            InvalidConfigError, match="num_hash_functions must be an integer"
        ):
            MinHash(num_hash_functions=128.5)

    def test_h_string_raises_invalid_config(self):
        with pytest.raises(
            InvalidConfigError, match="num_hash_functions must be an integer"
        ):
            MinHash(num_hash_functions="128")

    def test_h_none_raises_invalid_config(self):
        with pytest.raises(
            InvalidConfigError, match="num_hash_functions must be an integer"
        ):
            MinHash(num_hash_functions=None)

    def test_invalid_config_is_minhash_error(self):
        try:
            MinHash(num_hash_functions=0)
        except MinHashError:
            pass
        else:
            pytest.fail("Expected MinHashError")


class TestNonHashableElementExceptions:
    def test_adding_list_raises_non_hashable(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        with pytest.raises(NonHashableElementError, match="is not hashable"):
            mh.add([1, 2, 3])

    def test_adding_dict_raises_non_hashable(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        with pytest.raises(NonHashableElementError, match="is not hashable"):
            mh.add({"key": "value"})

    def test_adding_set_raises_non_hashable(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        with pytest.raises(NonHashableElementError, match="is not hashable"):
            mh.add({1, 2, 3})

    def test_adding_lambda_raises_non_hashable(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        with pytest.raises(NonHashableElementError, match="is not hashable"):
            mh.add(lambda x: x)

    def test_non_hashable_in_init_elements(self):
        with pytest.raises(NonHashableElementError, match="is not hashable"):
            MinHash(num_hash_functions=64, elements=[[1, 2], [3, 4]])

    def test_non_hashable_in_add_many(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        with pytest.raises(NonHashableElementError, match="is not hashable"):
            mh.add_many([1, 2, [3, 4]])

    def test_non_hashable_in_from_set(self):
        with pytest.raises(NonHashableElementError, match="is not hashable"):
            MinHash.from_set([{"a": 1}, {"b": 2}], num_hash_functions=64)

    def test_non_hashable_error_is_minhash_error(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        try:
            mh.add([1, 2, 3])
        except MinHashError:
            pass
        else:
            pytest.fail("Expected MinHashError")


class TestIncompatibleSignatureExceptions:
    def test_jaccard_different_h_raises(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        with pytest.raises(
            IncompatibleSignatureError, match="Signatures are incompatible"
        ):
            mh1.jaccard(mh2)

    def test_jaccard_different_seed_raises(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=123)
        with pytest.raises(
            IncompatibleSignatureError, match="Signatures are incompatible"
        ):
            mh1.jaccard(mh2)

    def test_jaccard_different_h_and_seed_raises(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=123)
        with pytest.raises(
            IncompatibleSignatureError, match="Signatures are incompatible"
        ):
            mh1.jaccard(mh2)

    def test_merge_different_h_raises(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        with pytest.raises(
            IncompatibleSignatureError, match="Signatures are incompatible"
        ):
            mh1.merge(mh2)

    def test_merge_different_seed_raises(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=123)
        with pytest.raises(
            IncompatibleSignatureError, match="Signatures are incompatible"
        ):
            mh1.merge(mh2)

    def test_in_place_merge_different_h_raises(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        with pytest.raises(
            IncompatibleSignatureError, match="Signatures are incompatible"
        ):
            mh1 |= mh2

    def test_in_place_merge_different_seed_raises(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=123)
        with pytest.raises(
            IncompatibleSignatureError, match="Signatures are incompatible"
        ):
            mh1 |= mh2

    def test_incompatible_error_message_contains_details(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=123)
        try:
            mh1.jaccard(mh2)
        except IncompatibleSignatureError as e:
            msg = str(e)
            assert "64" in msg
            assert "128" in msg
            assert "42" in msg
            assert "123" in msg
        else:
            pytest.fail("Expected IncompatibleSignatureError")

    def test_incompatible_signature_is_minhash_error(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        try:
            mh1.jaccard(mh2)
        except MinHashError:
            pass
        else:
            pytest.fail("Expected MinHashError")


class TestJaccardWithNonMinHash:
    def test_is_compatible_with_non_minhash(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        assert not mh.is_compatible("not a minhash")
        assert not mh.is_compatible(None)
        assert not mh.is_compatible(42)
        assert not mh.is_compatible([1, 2, 3])

    def test_equality_with_non_minhash(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        assert mh != "not a minhash"
        assert mh != None
        assert mh != 42
        assert (mh == [1, 2, 3]) is False


class TestExceptionHierarchy:
    def test_invalid_config_error_hierarchy(self):
        assert issubclass(InvalidConfigError, MinHashError)
        assert issubclass(MinHashError, Exception)

    def test_incompatible_signature_error_hierarchy(self):
        assert issubclass(IncompatibleSignatureError, MinHashError)
        assert issubclass(MinHashError, Exception)

    def test_non_hashable_element_error_hierarchy(self):
        assert issubclass(NonHashableElementError, MinHashError)
        assert issubclass(MinHashError, Exception)


class TestCheckCompatibleInternal:
    def test_check_compatible_different_h(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=128, seed=42)
        with pytest.raises(IncompatibleSignatureError):
            mh1._check_compatible(mh2)

    def test_check_compatible_different_seed(self):
        mh1 = MinHash(num_hash_functions=64, seed=42)
        mh2 = MinHash(num_hash_functions=64, seed=123)
        with pytest.raises(IncompatibleSignatureError):
            mh1._check_compatible(mh2)

    def test_check_compatible_non_minhash_type(self):
        mh = MinHash(num_hash_functions=64, seed=42)
        with pytest.raises(IncompatibleSignatureError):
            mh._check_compatible("not a minhash")
