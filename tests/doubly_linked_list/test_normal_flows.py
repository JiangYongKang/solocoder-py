import pytest

from solocoder_py.doubly_linked_list import DoublyLinkedList, Node


class TestPrependAppendOperations:
    def test_append_multiple_nodes(self, empty_list: DoublyLinkedList):
        n1 = empty_list.append(1)
        n2 = empty_list.append(2)
        n3 = empty_list.append(3)

        assert empty_list.size == 3
        assert len(empty_list) == 3
        assert empty_list.head is n1
        assert empty_list.tail is n3

        assert n1.prev is None
        assert n1.next is n2
        assert n2.prev is n1
        assert n2.next is n3
        assert n3.prev is n2
        assert n3.next is None

    def test_prepend_multiple_nodes(self, empty_list: DoublyLinkedList):
        n1 = empty_list.prepend(1)
        n2 = empty_list.prepend(2)
        n3 = empty_list.prepend(3)

        assert empty_list.size == 3
        assert empty_list.head is n3
        assert empty_list.tail is n1

        assert n3.prev is None
        assert n3.next is n2
        assert n2.prev is n3
        assert n2.next is n1
        assert n1.prev is n2
        assert n1.next is None

    def test_mixed_prepend_append(self, empty_list: DoublyLinkedList):
        n1 = empty_list.append(1)
        n2 = empty_list.prepend(2)
        n3 = empty_list.append(3)

        assert empty_list.size == 3
        assert empty_list.head is n2
        assert empty_list.tail is n3
        assert empty_list.to_list_forward() == [2, 1, 3]


class TestInsertAfterOperations:
    def test_insert_after_head(self, three_node_list: DoublyLinkedList):
        head = three_node_list.head
        new_node = three_node_list.insert_after(head, 10)

        assert three_node_list.size == 4
        assert three_node_list.to_list_forward() == [1, 10, 2, 3]
        assert head.next is new_node
        assert new_node.prev is head
        assert new_node.next is not None
        assert new_node.next.prev is new_node

    def test_insert_after_middle(self, three_node_list: DoublyLinkedList):
        middle = three_node_list.head.next
        new_node = three_node_list.insert_after(middle, 20)

        assert three_node_list.size == 4
        assert three_node_list.to_list_forward() == [1, 2, 20, 3]
        assert middle.next is new_node
        assert new_node.prev is middle
        assert new_node.next.data == 3
        assert three_node_list.tail.data == 3

    def test_insert_after_tail(self, three_node_list: DoublyLinkedList):
        tail = three_node_list.tail
        new_node = three_node_list.insert_after(tail, 30)

        assert three_node_list.size == 4
        assert three_node_list.to_list_forward() == [1, 2, 3, 30]
        assert three_node_list.tail is new_node
        assert tail.next is new_node
        assert new_node.prev is tail
        assert new_node.next is None


class TestDeleteOperations:
    def test_delete_head(self, three_node_list: DoublyLinkedList):
        old_head = three_node_list.head
        result = three_node_list.delete_head()

        assert result is True
        assert three_node_list.size == 2
        assert three_node_list.head.data == 2
        assert three_node_list.head.prev is None
        assert old_head.next is None
        assert old_head.prev is None

    def test_delete_tail(self, three_node_list: DoublyLinkedList):
        old_tail = three_node_list.tail
        result = three_node_list.delete_tail()

        assert result is True
        assert three_node_list.size == 2
        assert three_node_list.tail.data == 2
        assert three_node_list.tail.next is None
        assert old_tail.next is None
        assert old_tail.prev is None

    def test_delete_middle_node(self, three_node_list: DoublyLinkedList):
        middle = three_node_list.head.next
        result = three_node_list.delete_node(middle)

        assert result is True
        assert three_node_list.size == 2
        assert three_node_list.to_list_forward() == [1, 3]
        assert three_node_list.head.next is three_node_list.tail
        assert three_node_list.tail.prev is three_node_list.head
        assert middle.next is None
        assert middle.prev is None

    def test_delete_returns_node_pointers_cleared(self, three_node_list: DoublyLinkedList):
        middle = three_node_list.head.next
        three_node_list.delete_node(middle)
        assert middle.prev is None
        assert middle.next is None


class TestForwardBackwardTraversal:
    def test_forward_traversal(self, three_node_list: DoublyLinkedList):
        result = [node.data for node in three_node_list.iterate_forward()]
        assert result == [1, 2, 3]

    def test_backward_traversal(self, three_node_list: DoublyLinkedList):
        result = [node.data for node in three_node_list.iterate_backward()]
        assert result == [3, 2, 1]

    def test_to_list_forward(self, three_node_list: DoublyLinkedList):
        assert three_node_list.to_list_forward() == [1, 2, 3]

    def test_to_list_backward(self, three_node_list: DoublyLinkedList):
        assert three_node_list.to_list_backward() == [3, 2, 1]

    def test_iter_protocol(self, three_node_list: DoublyLinkedList):
        result = [node.data for node in three_node_list]
        assert result == [1, 2, 3]


class TestReverseOperations:
    def test_reverse_three_nodes(self, three_node_list: DoublyLinkedList):
        old_head = three_node_list.head
        old_tail = three_node_list.tail

        three_node_list.reverse()

        assert three_node_list.head is old_tail
        assert three_node_list.tail is old_head
        assert three_node_list.to_list_forward() == [3, 2, 1]
        assert three_node_list.to_list_backward() == [1, 2, 3]

    def test_reverse_two_nodes(self, empty_list: DoublyLinkedList):
        empty_list.append(1)
        empty_list.append(2)
        empty_list.reverse()
        assert empty_list.to_list_forward() == [2, 1]

    def test_double_reverse_identity(self, three_node_list: DoublyLinkedList):
        original = three_node_list.to_list_forward()
        three_node_list.reverse()
        three_node_list.reverse()
        assert three_node_list.to_list_forward() == original


class TestIsEmptyAndSize:
    def test_is_empty_true(self, empty_list: DoublyLinkedList):
        assert empty_list.is_empty() is True
        assert empty_list.size == 0
        assert len(empty_list) == 0

    def test_is_empty_false(self, single_node_list: DoublyLinkedList):
        assert single_node_list.is_empty() is False
        assert single_node_list.size == 1
        assert len(single_node_list) == 1

    def test_size_after_operations(self, empty_list: DoublyLinkedList):
        empty_list.append(1)
        empty_list.prepend(2)
        assert empty_list.size == 2
        empty_list.delete_head()
        assert empty_list.size == 1
        empty_list.delete_tail()
        assert empty_list.size == 0
        assert empty_list.is_empty()


class TestFindOperations:
    def test_find_existing(self, three_node_list: DoublyLinkedList):
        node = three_node_list.find(2)
        assert node is not None
        assert node.data == 2
        assert node.prev.data == 1
        assert node.next.data == 3

    def test_find_head(self, three_node_list: DoublyLinkedList):
        node = three_node_list.find(1)
        assert node is three_node_list.head

    def test_find_tail(self, three_node_list: DoublyLinkedList):
        node = three_node_list.find(3)
        assert node is three_node_list.tail

    def test_find_not_found(self, three_node_list: DoublyLinkedList):
        assert three_node_list.find(999) is None

    def test_find_empty(self, empty_list: DoublyLinkedList):
        assert empty_list.find(1) is None
