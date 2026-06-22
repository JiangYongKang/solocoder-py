import pytest

from solocoder_py.hashtable_chaining import HashTable


@pytest.fixture
def empty_ht():
    return HashTable[str, int]()


@pytest.fixture
def small_ht():
    ht = HashTable[str, int]()
    ht.put("apple", 1)
    ht.put("banana", 2)
    ht.put("cherry", 3)
    return ht


@pytest.fixture
def ht_with_custom_capacity():
    return HashTable[str, int](initial_capacity=4, load_factor_threshold=0.5)
