import pytest

from solocoder_py.autocomplete import TrieAutocomplete


@pytest.fixture
def empty_trie() -> TrieAutocomplete:
    return TrieAutocomplete()


@pytest.fixture
def sample_trie() -> TrieAutocomplete:
    trie = TrieAutocomplete()
    trie.insert("apple", weight=10)
    trie.insert("app", weight=8)
    trie.insert("application", weight=15)
    trie.insert("banana", weight=12)
    trie.insert("ball", weight=5)
    trie.insert("cat", weight=7)
    trie.insert("car", weight=9)
    return trie


@pytest.fixture
def case_sensitive_trie() -> TrieAutocomplete:
    trie = TrieAutocomplete(case_sensitive=True)
    trie.insert("Apple", weight=10)
    trie.insert("apple", weight=8)
    trie.insert("APP", weight=15)
    return trie


@pytest.fixture
def chinese_trie() -> TrieAutocomplete:
    trie = TrieAutocomplete()
    trie.insert("中国", weight=10)
    trie.insert("中国人", weight=15)
    trie.insert("中国话", weight=8)
    trie.insert("北京", weight=12)
    trie.insert("北京大学", weight=20)
    return trie
