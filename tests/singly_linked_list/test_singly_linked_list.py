import pytest

from solocoder_py.singly_linked_list import (
    Node,
    SinglyLinkedList,
    SinglyLinkedListError,
)


class TestEmptyList:
    def test_new_list_is_empty(self, linked_list: SinglyLinkedList):
        assert linked_list.is_empty() is True
        assert linked_list.size() == 0
        assert len(linked_list) == 0

    def test_empty_list_head_tail_none(self, linked_list: SinglyLinkedList):
        assert linked_list.head is None
        assert linked_list.tail is None

    def test_empty_list_traverse(self, linked_list: SinglyLinkedList):
        assert linked_list.traverse() == []

    def test_empty_list_find_returns_none(self, linked_list: SinglyLinkedList):
        assert linked_list.find(1) is None

    def test_empty_list_remove_returns_false(self, linked_list: SinglyLinkedList):
        assert linked_list.remove(1) is False

    def test_empty_list_reverse_no_error(self, linked_list: SinglyLinkedList):
        linked_list.reverse()
        assert linked_list.is_empty() is True
        assert linked_list.traverse() == []

    def test_empty_list_iteration(self, linked_list: SinglyLinkedList):
        items = list(linked_list)
        assert items == []


class TestPrepend:
    def test_prepend_to_empty_list(self, linked_list: SinglyLinkedList):
        node = linked_list.prepend(1)
        assert isinstance(node, Node)
        assert node.value == 1
        assert linked_list.head is node
        assert linked_list.tail is node
        assert linked_list.size() == 1
        assert linked_list.is_empty() is False

    def test_prepend_multiple_values(self, linked_list: SinglyLinkedList):
        linked_list.prepend(3)
        linked_list.prepend(2)
        linked_list.prepend(1)

        assert linked_list.traverse() == [1, 2, 3]
        assert linked_list.head.value == 1
        assert linked_list.tail.value == 3
        assert len(linked_list) == 3

    def test_prepend_returns_node(self, linked_list: SinglyLinkedList):
        node = linked_list.prepend(42)
        assert node.value == 42
        assert linked_list.head is node


class TestAppend:
    def test_append_to_empty_list(self, linked_list: SinglyLinkedList):
        node = linked_list.append(1)
        assert isinstance(node, Node)
        assert node.value == 1
        assert linked_list.head is node
        assert linked_list.tail is node
        assert linked_list.size() == 1
        assert linked_list.is_empty() is False

    def test_append_multiple_values(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        linked_list.append(2)
        linked_list.append(3)

        assert linked_list.traverse() == [1, 2, 3]
        assert linked_list.head.value == 1
        assert linked_list.tail.value == 3
        assert len(linked_list) == 3

    def test_append_returns_node(self, linked_list: SinglyLinkedList):
        node = linked_list.append(42)
        assert node.value == 42
        assert linked_list.tail is node


class TestMixedPrependAppend:
    def test_mixed_operations(self, linked_list: SinglyLinkedList):
        linked_list.append(2)
        linked_list.prepend(1)
        linked_list.append(3)
        linked_list.prepend(0)

        assert linked_list.traverse() == [0, 1, 2, 3]
        assert linked_list.size() == 4

    def test_append_prepend_maintains_tail(self, linked_list: SinglyLinkedList):
        linked_list.prepend(1)
        linked_list.append(2)
        assert linked_list.tail.value == 2

        linked_list.prepend(0)
        assert linked_list.tail.value == 2


class TestFind:
    def test_find_existing_value(self, filled_list: SinglyLinkedList):
        node = filled_list.find(3)
        assert node is not None
        assert node.value == 3

    def test_find_head_value(self, filled_list: SinglyLinkedList):
        node = filled_list.find(1)
        assert node is not None
        assert node is filled_list.head

    def test_find_tail_value(self, filled_list: SinglyLinkedList):
        node = filled_list.find(5)
        assert node is not None
        assert node is filled_list.tail

    def test_find_nonexistent_value(self, filled_list: SinglyLinkedList):
        assert filled_list.find(99) is None
        assert filled_list.find(0) is None

    def test_find_empty_list(self, linked_list: SinglyLinkedList):
        assert linked_list.find(1) is None


class TestRemove:
    def test_remove_head_value(self, filled_list: SinglyLinkedList):
        result = filled_list.remove(1)
        assert result is True
        assert filled_list.traverse() == [2, 3, 4, 5]
        assert filled_list.head.value == 2
        assert filled_list.size() == 4

    def test_remove_tail_value(self, filled_list: SinglyLinkedList):
        result = filled_list.remove(5)
        assert result is True
        assert filled_list.traverse() == [1, 2, 3, 4]
        assert filled_list.tail.value == 4
        assert filled_list.size() == 4

    def test_remove_middle_value(self, filled_list: SinglyLinkedList):
        result = filled_list.remove(3)
        assert result is True
        assert filled_list.traverse() == [1, 2, 4, 5]
        assert filled_list.size() == 4

    def test_remove_nonexistent_value(self, filled_list: SinglyLinkedList):
        result = filled_list.remove(99)
        assert result is False
        assert filled_list.size() == 5
        assert filled_list.traverse() == [1, 2, 3, 4, 5]

    def test_remove_from_empty_list(self, linked_list: SinglyLinkedList):
        result = linked_list.remove(1)
        assert result is False
        assert linked_list.is_empty() is True

    def test_remove_only_node(self, linked_list: SinglyLinkedList):
        linked_list.append(42)
        result = linked_list.remove(42)
        assert result is True
        assert linked_list.is_empty() is True
        assert linked_list.head is None
        assert linked_list.tail is None
        assert linked_list.size() == 0

    def test_remove_first_of_two(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        linked_list.append(2)
        linked_list.remove(1)
        assert linked_list.traverse() == [2]
        assert linked_list.head.value == 2
        assert linked_list.tail.value == 2
        assert linked_list.size() == 1

    def test_remove_second_of_two(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        linked_list.append(2)
        linked_list.remove(2)
        assert linked_list.traverse() == [1]
        assert linked_list.head.value == 1
        assert linked_list.tail.value == 1
        assert linked_list.size() == 1


class TestReverse:
    def test_reverse_filled_list(self, filled_list: SinglyLinkedList):
        original_head = filled_list.head
        original_tail = filled_list.tail

        filled_list.reverse()

        assert filled_list.traverse() == [5, 4, 3, 2, 1]
        assert filled_list.head is original_tail
        assert filled_list.tail is original_head

    def test_reverse_twice(self, filled_list: SinglyLinkedList):
        original = filled_list.traverse()
        filled_list.reverse()
        filled_list.reverse()
        assert filled_list.traverse() == original

    def test_reverse_empty_list(self, linked_list: SinglyLinkedList):
        linked_list.reverse()
        assert linked_list.is_empty() is True
        assert linked_list.head is None
        assert linked_list.tail is None

    def test_reverse_single_node(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        original_head = linked_list.head
        original_tail = linked_list.tail

        linked_list.reverse()

        assert linked_list.traverse() == [1]
        assert linked_list.head is original_head
        assert linked_list.tail is original_tail
        assert linked_list.size() == 1

    def test_reverse_two_nodes(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        linked_list.append(2)
        linked_list.reverse()
        assert linked_list.traverse() == [2, 1]
        assert linked_list.head.value == 2
        assert linked_list.tail.value == 1


class TestTraverse:
    def test_traverse_filled_list(self, filled_list: SinglyLinkedList):
        assert filled_list.traverse() == [1, 2, 3, 4, 5]

    def test_traverse_empty_list(self, linked_list: SinglyLinkedList):
        assert linked_list.traverse() == []

    def test_traverse_single_node(self, linked_list: SinglyLinkedList):
        linked_list.append(42)
        assert linked_list.traverse() == [42]

    def test_traverse_after_modifications(self, filled_list: SinglyLinkedList):
        filled_list.remove(3)
        filled_list.prepend(0)
        filled_list.append(6)
        assert filled_list.traverse() == [0, 1, 2, 4, 5, 6]


class TestIteration:
    def test_iterate_filled_list(self, filled_list: SinglyLinkedList):
        result = []
        for val in filled_list:
            result.append(val)
        assert result == [1, 2, 3, 4, 5]

    def test_iterate_empty_list(self, linked_list: SinglyLinkedList):
        result = list(linked_list)
        assert result == []


class TestIsEmpty:
    def test_empty_list_is_empty(self, linked_list: SinglyLinkedList):
        assert linked_list.is_empty() is True

    def test_non_empty_list_not_empty(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        assert linked_list.is_empty() is False

    def test_after_removing_all_is_empty(self, filled_list: SinglyLinkedList):
        for i in range(1, 6):
            filled_list.remove(i)
        assert filled_list.is_empty() is True


class TestSize:
    def test_empty_list_size_zero(self, linked_list: SinglyLinkedList):
        assert linked_list.size() == 0
        assert len(linked_list) == 0

    def test_size_after_operations(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        assert linked_list.size() == 1

        linked_list.prepend(0)
        assert len(linked_list) == 2

        linked_list.append(2)
        assert linked_list.size() == 3

        linked_list.remove(1)
        assert len(linked_list) == 2

    def test_size_after_remove_all(self, filled_list: SinglyLinkedList):
        filled_list.remove(1)
        filled_list.remove(3)
        filled_list.remove(5)
        assert filled_list.size() == 2

        filled_list.remove(2)
        filled_list.remove(4)
        assert filled_list.size() == 0


class TestHeadTail:
    def test_head_tail_single_node(self, linked_list: SinglyLinkedList):
        node = linked_list.append(42)
        assert linked_list.head is node
        assert linked_list.tail is node

    def test_head_tail_multiple_nodes(self, filled_list: SinglyLinkedList):
        assert filled_list.head.value == 1
        assert filled_list.tail.value == 5

    def test_head_tail_after_remove_head(self, filled_list: SinglyLinkedList):
        filled_list.remove(1)
        assert filled_list.head.value == 2
        assert filled_list.tail.value == 5

    def test_head_tail_after_remove_tail(self, filled_list: SinglyLinkedList):
        filled_list.remove(5)
        assert filled_list.head.value == 1
        assert filled_list.tail.value == 4

    def test_head_tail_after_reverse(self, filled_list: SinglyLinkedList):
        filled_list.reverse()
        assert filled_list.head.value == 5
        assert filled_list.tail.value == 1


class TestSingleNodeEdgeCases:
    def test_remove_then_add(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        linked_list.remove(1)
        assert linked_list.is_empty() is True

        linked_list.append(2)
        assert linked_list.traverse() == [2]
        assert linked_list.head.value == 2
        assert linked_list.tail.value == 2

    def test_single_node_reverse_then_remove(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        linked_list.reverse()
        assert linked_list.remove(1) is True
        assert linked_list.is_empty() is True


class TestContinuousDeleteUntilEmpty:
    def test_delete_from_head_until_empty(self, linked_list: SinglyLinkedList):
        for i in range(5):
            linked_list.append(i)

        for i in range(5):
            assert linked_list.remove(i) is True
            assert linked_list.size() == 4 - i

        assert linked_list.is_empty() is True
        assert linked_list.head is None
        assert linked_list.tail is None

    def test_delete_from_tail_until_empty(self, linked_list: SinglyLinkedList):
        for i in range(5):
            linked_list.append(i)

        for i in range(4, -1, -1):
            assert linked_list.remove(i) is True

        assert linked_list.is_empty() is True
        assert linked_list.head is None
        assert linked_list.tail is None

    def test_delete_middle_until_empty(self, linked_list: SinglyLinkedList):
        for i in [1, 3, 5, 7, 9]:
            linked_list.append(i)

        order = [5, 3, 7, 1, 9]
        for val in order:
            assert linked_list.remove(val) is True

        assert linked_list.is_empty() is True

    def test_delete_nonexistent_while_deleting(self, linked_list: SinglyLinkedList):
        linked_list.append(1)
        linked_list.append(2)

        assert linked_list.remove(1) is True
        assert linked_list.remove(1) is False
        assert linked_list.size() == 1
        assert linked_list.remove(2) is True
        assert linked_list.remove(2) is False
        assert linked_list.is_empty() is True


class TestNodeClass:
    def test_node_creation(self):
        node = Node(value=42)
        assert node.value == 42
        assert node.next is None

    def test_node_with_next(self):
        node2 = Node(value=2)
        node1 = Node(value=1, next=node2)
        assert node1.next is node2
        assert node1.next.value == 2

    def test_node_repr(self):
        node = Node(value="test")
        assert "test" in repr(node)


class TestExceptionHierarchy:
    def test_singly_linked_list_error_is_exception(self):
        assert issubclass(SinglyLinkedListError, Exception)


class TestValueEqualitySemantics:
    def test_find_uses_double_equals(self, linked_list: SinglyLinkedList):
        class EqualToEverything:
            def __eq__(self, other):
                return True

        linked_list.append(42)
        node = linked_list.find(EqualToEverything())
        assert node is not None
        assert node.value == 42

    def test_remove_uses_double_equals(self, linked_list: SinglyLinkedList):
        class MatchesEven:
            def __eq__(self, other):
                return isinstance(other, int) and other % 2 == 0

        linked_list.append(1)
        linked_list.append(2)
        linked_list.append(3)

        assert linked_list.remove(MatchesEven()) is True
        assert linked_list.traverse() == [1, 3]

    def test_custom_equality_not_implemented_uses_identity(self, linked_list: SinglyLinkedList):
        class NoEq:
            def __init__(self, val):
                self.val = val

        obj = NoEq(1)
        linked_list.append(obj)

        assert linked_list.find(NoEq(1)) is None
        assert linked_list.find(obj) is not None


class TestRepr:
    def test_repr_empty(self, linked_list: SinglyLinkedList):
        assert "SinglyLinkedList" in repr(linked_list)

    def test_repr_with_values(self, filled_list: SinglyLinkedList):
        r = repr(filled_list)
        assert "1" in r
        assert "5" in r
        assert "->" in r
