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

