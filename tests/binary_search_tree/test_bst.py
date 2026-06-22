import pytest

from solocoder_py.binary_search_tree import (
    BinarySearchTree,
    DuplicateValueError,
    ValueNotFoundError,
)


class TestInsertOperation:
    def test_insert_into_empty_tree(self, bst: BinarySearchTree):
        bst.insert(5)
        assert bst.size() == 1
        assert bst.search(5) is True
        assert bst.root is not None
        assert bst.root.value == 5

    def test_insert_multiple_values(self, bst: BinarySearchTree):
        values = [8, 3, 10, 1, 6, 14]
        for v in values:
            bst.insert(v)
        assert bst.size() == 6
        for v in values:
            assert bst.search(v) is True

    def test_insert_maintains_bst_property(self, bst: BinarySearchTree):
        values = [8, 3, 10, 1, 6, 14, 4, 7, 13]
        for v in values:
            bst.insert(v)
        inorder = bst.inorder_traversal()
        assert inorder == sorted(values)

    def test_insert_duplicate_raises_error(self, bst: BinarySearchTree):
        bst.insert(5)
        with pytest.raises(DuplicateValueError):
            bst.insert(5)
        assert bst.size() == 1

    def test_insert_duplicate_in_populated_tree(self, populated_bst: BinarySearchTree):
        original_size = populated_bst.size()
        with pytest.raises(DuplicateValueError):
            populated_bst.insert(3)
        assert populated_bst.size() == original_size


class TestSearchOperation:
    def test_search_existing_value(self, populated_bst: BinarySearchTree):
        assert populated_bst.search(8) is True
        assert populated_bst.search(1) is True
        assert populated_bst.search(14) is True
        assert populated_bst.search(7) is True

    def test_search_nonexistent_value(self, populated_bst: BinarySearchTree):
        assert populated_bst.search(99) is False
        assert populated_bst.search(0) is False
        assert populated_bst.search(20) is False

    def test_search_in_empty_tree(self, bst: BinarySearchTree):
        assert bst.search(5) is False


class TestDeleteLeafNode:
    def test_delete_leaf_node(self, populated_bst: BinarySearchTree):
        assert populated_bst.search(1) is True
        populated_bst.delete(1)
        assert populated_bst.search(1) is False
        assert populated_bst.size() == 8
        assert populated_bst.inorder_traversal() == [3, 4, 6, 7, 8, 10, 13, 14]

    def test_delete_right_leaf(self, populated_bst: BinarySearchTree):
        populated_bst.delete(13)
        assert populated_bst.search(13) is False
        assert populated_bst.size() == 8


class TestDeleteNodeWithOneChild:
    def test_delete_node_with_left_child(self, bst: BinarySearchTree):
        bst.insert(10)
        bst.insert(5)
        bst.insert(3)
        bst.delete(5)
        assert bst.search(5) is False
        assert bst.search(3) is True
        assert bst.search(10) is True
        assert bst.size() == 2
        assert bst.inorder_traversal() == [3, 10]

    def test_delete_node_with_right_child(self, bst: BinarySearchTree):
        bst.insert(10)
        bst.insert(15)
        bst.insert(20)
        bst.delete(15)
        assert bst.search(15) is False
        assert bst.search(20) is True
        assert bst.search(10) is True
        assert bst.size() == 2
        assert bst.inorder_traversal() == [10, 20]

    def test_delete_node_with_one_child_maintains_bst(self, populated_bst: BinarySearchTree):
        populated_bst.delete(10)
        assert populated_bst.search(10) is False
        assert populated_bst.inorder_traversal() == [1, 3, 4, 6, 7, 8, 13, 14]


class TestDeleteNodeWithTwoChildren:
    def test_delete_node_with_two_children(self, populated_bst: BinarySearchTree):
        populated_bst.delete(3)
        assert populated_bst.search(3) is False
        assert populated_bst.search(1) is True
        assert populated_bst.search(6) is True
        assert populated_bst.search(4) is True
        assert populated_bst.search(7) is True
        assert populated_bst.size() == 8
        assert populated_bst.inorder_traversal() == [1, 4, 6, 7, 8, 10, 13, 14]

    def test_delete_root_with_two_children(self, populated_bst: BinarySearchTree):
        populated_bst.delete(8)
        assert populated_bst.search(8) is False
        assert populated_bst.size() == 8
        inorder = populated_bst.inorder_traversal()
        assert inorder == sorted(inorder)
        assert 1 in inorder
        assert 14 in inorder

    def test_delete_internal_node_with_two_children(self, bst: BinarySearchTree):
        for v in [50, 30, 70, 20, 40, 60, 80]:
            bst.insert(v)
        bst.delete(50)
        assert bst.search(50) is False
        assert bst.size() == 6
        assert bst.inorder_traversal() == [20, 30, 40, 60, 70, 80]


class TestDeleteRootNode:
    def test_delete_root_single_node(self, bst: BinarySearchTree):
        bst.insert(42)
        bst.delete(42)
        assert bst.is_empty() is True
        assert bst.size() == 0
        assert bst.search(42) is False

    def test_delete_root_with_only_left_child(self, bst: BinarySearchTree):
        bst.insert(10)
        bst.insert(5)
        bst.delete(10)
        assert bst.size() == 1
        assert bst.root is not None
        assert bst.root.value == 5

    def test_delete_root_with_only_right_child(self, bst: BinarySearchTree):
        bst.insert(10)
        bst.insert(15)
        bst.delete(10)
        assert bst.size() == 1
        assert bst.root is not None
        assert bst.root.value == 15

    def test_delete_root_with_two_children(self, bst: BinarySearchTree):
        bst.insert(10)
        bst.insert(5)
        bst.insert(15)
        bst.delete(10)
        assert bst.size() == 2
        assert bst.search(5) is True
        assert bst.search(15) is True
        assert bst.inorder_traversal() == [5, 15]


class TestDeleteNonexistentValue:
    def test_delete_from_empty_tree_raises(self, bst: BinarySearchTree):
        with pytest.raises(ValueNotFoundError):
            bst.delete(5)

    def test_delete_nonexistent_value_raises(self, populated_bst: BinarySearchTree):
        original_size = populated_bst.size()
        original_inorder = populated_bst.inorder_traversal()
        with pytest.raises(ValueNotFoundError):
            populated_bst.delete(99)
        assert populated_bst.size() == original_size
        assert populated_bst.inorder_traversal() == original_inorder


class TestTraversalOperations:
    def test_preorder_traversal(self, populated_bst: BinarySearchTree):
        result = populated_bst.preorder_traversal()
        assert result == [8, 3, 1, 6, 4, 7, 10, 14, 13]

    def test_inorder_traversal(self, populated_bst: BinarySearchTree):
        result = populated_bst.inorder_traversal()
        assert result == [1, 3, 4, 6, 7, 8, 10, 13, 14]

    def test_postorder_traversal(self, populated_bst: BinarySearchTree):
        result = populated_bst.postorder_traversal()
        assert result == [1, 4, 7, 6, 3, 13, 14, 10, 8]

    def test_preorder_empty_tree(self, bst: BinarySearchTree):
        assert bst.preorder_traversal() == []

    def test_inorder_empty_tree(self, bst: BinarySearchTree):
        assert bst.inorder_traversal() == []

    def test_postorder_empty_tree(self, bst: BinarySearchTree):
        assert bst.postorder_traversal() == []

    def test_inorder_is_sorted(self, bst: BinarySearchTree):
        import random
        values = list(range(100))
        random.shuffle(values)
        for v in values:
            bst.insert(v)
        assert bst.inorder_traversal() == sorted(values)


class TestTreeQueries:
    def test_is_empty_true(self, bst: BinarySearchTree):
        assert bst.is_empty() is True

    def test_is_empty_false(self, bst: BinarySearchTree):
        bst.insert(1)
        assert bst.is_empty() is False

    def test_size_empty_tree(self, bst: BinarySearchTree):
        assert bst.size() == 0

    def test_size_after_insertions(self, bst: BinarySearchTree):
        for i in range(5):
            bst.insert(i)
        assert bst.size() == 5

    def test_size_after_deletions(self, populated_bst: BinarySearchTree):
        initial = populated_bst.size()
        populated_bst.delete(1)
        assert populated_bst.size() == initial - 1
        populated_bst.delete(3)
        assert populated_bst.size() == initial - 2


class TestSingleNodeTree:
    def test_single_node_insert(self, bst: BinarySearchTree):
        bst.insert(42)
        assert bst.size() == 1
        assert bst.is_empty() is False
        assert bst.search(42) is True

    def test_single_node_delete(self, bst: BinarySearchTree):
        bst.insert(42)
        bst.delete(42)
        assert bst.is_empty() is True
        assert bst.size() == 0

    def test_single_node_traversals(self, bst: BinarySearchTree):
        bst.insert(42)
        assert bst.preorder_traversal() == [42]
        assert bst.inorder_traversal() == [42]
        assert bst.postorder_traversal() == [42]


class TestClearOperation:
    def test_clear_populated_tree(self, populated_bst: BinarySearchTree):
        populated_bst.clear()
        assert populated_bst.is_empty() is True
        assert populated_bst.size() == 0
        assert populated_bst.preorder_traversal() == []

    def test_clear_empty_tree(self, bst: BinarySearchTree):
        bst.clear()
        assert bst.is_empty() is True
        assert bst.size() == 0

    def test_clear_then_insert(self, populated_bst: BinarySearchTree):
        populated_bst.clear()
        populated_bst.insert(100)
        assert populated_bst.size() == 1
        assert populated_bst.search(100) is True


class TestEdgeCases:
    def test_insert_negative_values(self, bst: BinarySearchTree):
        bst.insert(-5)
        bst.insert(-10)
        bst.insert(-3)
        assert bst.inorder_traversal() == [-10, -5, -3]
        assert bst.size() == 3

    def test_insert_zero(self, bst: BinarySearchTree):
        bst.insert(0)
        assert bst.search(0) is True
        assert bst.size() == 1

    def test_large_values(self, bst: BinarySearchTree):
        bst.insert(10**9)
        bst.insert(-10**9)
        assert bst.size() == 2
        assert bst.inorder_traversal() == [-10**9, 10**9]

    def test_left_skewed_tree(self, bst: BinarySearchTree):
        values = [5, 4, 3, 2, 1]
        for v in values:
            bst.insert(v)
        assert bst.inorder_traversal() == [1, 2, 3, 4, 5]
        assert bst.preorder_traversal() == [5, 4, 3, 2, 1]
        assert bst.postorder_traversal() == [1, 2, 3, 4, 5]

    def test_right_skewed_tree(self, bst: BinarySearchTree):
        values = [1, 2, 3, 4, 5]
        for v in values:
            bst.insert(v)
        assert bst.inorder_traversal() == [1, 2, 3, 4, 5]
        assert bst.preorder_traversal() == [1, 2, 3, 4, 5]
        assert bst.postorder_traversal() == [5, 4, 3, 2, 1]

    def test_delete_from_skewed_tree(self, bst: BinarySearchTree):
        values = [1, 2, 3, 4, 5]
        for v in values:
            bst.insert(v)
        bst.delete(3)
        assert bst.search(3) is False
        assert bst.size() == 4
        assert bst.inorder_traversal() == [1, 2, 4, 5]
