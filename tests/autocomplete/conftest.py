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
