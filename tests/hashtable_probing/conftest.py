import pytest

from solocoder_py.hashtable_probing import ProbingHashTable


@pytest.fixture
def ht() -> ProbingHashTable:
    return ProbingHashTable(initial_capacity=8)
