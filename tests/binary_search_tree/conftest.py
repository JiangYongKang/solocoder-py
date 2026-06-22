import pytest

from solocoder_py.binary_search_tree import BinarySearchTree


@pytest.fixture
def bst() -> BinarySearchTree:
    return BinarySearchTree()


@pytest.fixture
def populated_bst() -> BinarySearchTree:
    tree = BinarySearchTree()
    for value in [8, 3, 10, 1, 6, 14, 4, 7, 13]:
        tree.insert(value)
    return tree
