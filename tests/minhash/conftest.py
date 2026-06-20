from __future__ import annotations

import pytest

from solocoder_py.minhash import MinHash


@pytest.fixture
def small_minhash():
    return MinHash(num_hash_functions=64, seed=42)


@pytest.fixture
def large_minhash():
    return MinHash(num_hash_functions=256, seed=42)


@pytest.fixture
def minhash_with_elements():
    mh = MinHash(num_hash_functions=128, seed=42)
    for i in range(100):
        mh.add(f"element_{i}")
    return mh
