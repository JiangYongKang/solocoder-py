import pytest

from solocoder_py.doubly_linked_list import (
    DoublyLinkedList,
    Node,
    NodeNotFoundError,
)


class TestEmptyListOperations:
    def test_delete_head_empty_returns_false(self, empty_list: DoublyLinkedList):
        result = empty_list.delete_head()
        assert result is False
        assert empty_list.is_empty()
        assert empty_list.size == 0

    def test_delete_tail_empty_returns_false(self, empty_list: DoublyLinkedList):
        result = empty_list.delete_tail()
        assert result is False
        assert empty_list.is_empty()

    def test_delete_node_empty_returns_false(self, empty_list: DoublyLinkedList):
        node = Node(data=1)
        result = empty_list.delete_node(node)
        assert result is False

    def test_iterate_forward_empty_safe(self, empty_list: DoublyLinkedList):
        result = list(empty_list.iterate_forward())
        assert result == []

    def test_iterate_backward_empty_safe(self, empty_list: DoublyLinkedList):
        result = list(empty_list.iterate_backward())
        assert result == []

    def test_reverse_empty_no_op(self, empty_list: DoublyLinkedList):
        empty_list.reverse()
        assert empty_list.is_empty()
        assert empty_list.head is None
        assert empty_list.tail is None

    def test_head_tail_none_empty(self, empty_list: DoublyLinkedList):
        assert empty_list.head is None
        assert empty_list.tail is None

    def test_to_list_forward_empty(self, empty_list: DoublyLinkedList):
        assert empty_list.to_list_forward() == []

    def test_to_list_backward_empty(self, empty_list: DoublyLinkedList):
        assert empty_list.to_list_backward() == []

    def test_insert_after_none_raises(self, empty_list: DoublyLinkedList):
        with pytest.raises(NodeNotFoundError):
            empty_list.insert_after(None, 1)


class TestSingleNodeListOperations:
    def test_append_single_node_pointers_none(self, empty_list: DoublyLinkedList):
        node = empty_list.append(1)
        assert node.prev is None
        assert node.next is None
        assert empty_list.head is node
        assert empty_list.tail is node

    def test_prepend_single_node_pointers_none(self, empty_list: DoublyLinkedList):
        node = empty_list.prepend(1)
        assert node.prev is None
        assert node.next is None
        assert empty_list.head is node
        assert empty_list.tail is node

    def test_delete_single_node_head_both_null(self, single_node_list: DoublyLinkedList):
        single_node_list.delete_head()
        assert single_node_list.head is None
        assert single_node_list.tail is None
        assert single_node_list.is_empty()
        assert single_node_list.size == 0

    def test_delete_single_node_tail_both_null(self, single_node_list: DoublyLinkedList):
        single_node_list.delete_tail()
        assert single_node_list.head is None
        assert single_node_list.tail is None
        assert single_node_list.is_empty()

    def test_delete_single_node_pointers_cleared(self, single_node_list: DoublyLinkedList):
        node = single_node_list.head
        single_node_list.delete_node(node)
        assert node.prev is None
        assert node.next is None

    def test_reverse_single_node_no_change(self, single_node_list: DoublyLinkedList):
        original_head = single_node_list.head
        original_tail = single_node_list.tail
        single_node_list.reverse()
        assert single_node_list.head is original_head
        assert single_node_list.tail is original_tail
        assert single_node_list.to_list_forward() == [1]

    def test_insert_after_single_node(self, single_node_list: DoublyLinkedList):
        head = single_node_list.head
        new_node = single_node_list.insert_after(head, 2)
        assert single_node_list.size == 2
        assert single_node_list.tail is new_node
        assert head.next is new_node
        assert new_node.prev is head
        assert new_node.next is None
        assert head.prev is None


class TestHeadTailNodeDeletion:
    def test_delete_head_updates_adjacent_prev(self, three_node_list: DoublyLinkedList):
        old_head = three_node_list.head
        new_head_expected = old_head.next

        three_node_list.delete_head()

        assert three_node_list.head is new_head_expected
        assert new_head_expected.prev is None
        assert new_head_expected.next.data == 3

    def test_delete_tail_updates_adjacent_next(self, three_node_list: DoublyLinkedList):
        old_tail = three_node_list.tail
        new_tail_expected = old_tail.prev

        three_node_list.delete_tail()

        assert three_node_list.tail is new_tail_expected
        assert new_tail_expected.next is None
        assert new_tail_expected.prev.data == 1

    def test_delete_head_from_two_nodes(self, empty_list: DoublyLinkedList):
        empty_list.append(1)
        empty_list.append(2)

        empty_list.delete_head()

        assert empty_list.size == 1
        assert empty_list.head.data == 2
        assert empty_list.tail.data == 2
        assert empty_list.head.prev is None
        assert empty_list.head.next is None

    def test_delete_tail_from_two_nodes(self, empty_list: DoublyLinkedList):
        empty_list.append(1)
        empty_list.append(2)

        empty_list.delete_tail()

        assert empty_list.size == 1
        assert empty_list.head.data == 1
        assert empty_list.tail.data == 1
        assert empty_list.head.prev is None
        assert empty_list.head.next is None


class TestDeleteNodeNotInList:
    def test_delete_external_node_returns_false(self, three_node_list: DoublyLinkedList):
        external_node = Node(data=99)
        result = three_node_list.delete_node(external_node)
        assert result is False
        assert three_node_list.size == 3
        assert three_node_list.to_list_forward() == [1, 2, 3]

    def test_delete_already_deleted_node(self, three_node_list: DoublyLinkedList):
        middle = three_node_list.head.next
        three_node_list.delete_node(middle)
        result = three_node_list.delete_node(middle)
        assert result is False

    def test_delete_none_node_returns_false(self, three_node_list: DoublyLinkedList):
        result = three_node_list.delete_node(None)
        assert result is False

    def test_insert_after_external_node_raises(self, three_node_list: DoublyLinkedList):
        external_node = Node(data=99)
        with pytest.raises(NodeNotFoundError):
            three_node_list.insert_after(external_node, 100)

    def test_insert_after_none_node_raises(self, three_node_list: DoublyLinkedList):
        with pytest.raises(NodeNotFoundError):
            three_node_list.insert_after(None, 100)


class TestConsecutiveOperationsIntegrity:
    def test_alternating_prepend_append(self, empty_list: DoublyLinkedList):
        empty_list.prepend(1)
        empty_list.append(2)
        empty_list.prepend(0)
        empty_list.append(3)

        assert empty_list.to_list_forward() == [0, 1, 2, 3]
        assert empty_list.to_list_backward() == [3, 2, 1, 0]
        assert empty_list.head.prev is None
        assert empty_list.tail.next is None
        assert empty_list.size == 4

    def test_delete_all_nodes_one_by_one_from_head(self, three_node_list: DoublyLinkedList):
        three_node_list.delete_head()
        assert three_node_list.to_list_forward() == [2, 3]
        three_node_list.delete_head()
        assert three_node_list.to_list_forward() == [3]
        three_node_list.delete_head()
        assert three_node_list.is_empty()
        assert three_node_list.head is None
        assert three_node_list.tail is None

    def test_delete_all_nodes_one_by_one_from_tail(self, three_node_list: DoublyLinkedList):
        three_node_list.delete_tail()
        assert three_node_list.to_list_forward() == [1, 2]
        three_node_list.delete_tail()
        assert three_node_list.to_list_forward() == [1]
        three_node_list.delete_tail()
        assert three_node_list.is_empty()
        assert three_node_list.head is None
        assert three_node_list.tail is None

    def test_insert_and_delete_mixed(self, empty_list: DoublyLinkedList):
        n1 = empty_list.append(1)
        n2 = empty_list.append(2)
        n3 = empty_list.append(3)

        empty_list.insert_after(n2, 2.5)
        assert empty_list.to_list_forward() == [1, 2, 2.5, 3]

        empty_list.delete_node(n2)
        assert empty_list.to_list_forward() == [1, 2.5, 3]

        empty_list.delete_node(n1)
        assert empty_list.to_list_forward() == [2.5, 3]
        assert empty_list.head.prev is None

        empty_list.delete_node(n3)
        assert empty_list.to_list_forward() == [2.5]
        assert empty_list.head is empty_list.tail

    def test_multiple_reverses(self, empty_list: DoublyLinkedList):
        for i in range(5):
            empty_list.append(i)

        original = empty_list.to_list_forward()
        for i in range(3):
            empty_list.reverse()
        assert empty_list.to_list_forward() == list(reversed(original))
        empty_list.reverse()
        assert empty_list.to_list_forward() == original

    def test_insert_delete_after_then_before_neighbors(self, empty_list: DoublyLinkedList):
        n1 = empty_list.append(1)
        n2 = empty_list.append(2)
        n3 = empty_list.append(3)
        n4 = empty_list.append(4)

        empty_list.delete_node(n2)
        empty_list.delete_node(n3)

        assert empty_list.to_list_forward() == [1, 4]
        assert n1.next is n4
        assert n4.prev is n1
        assert n1.prev is None
        assert n4.next is None

    def test_rep_populated_contains_data(self, three_node_list: DoublyLinkedList):
        repr_str = repr(three_node_list)
        assert "DoublyLinkedList" in repr_str
        assert "1" in repr_str
        assert "2" in repr_str
        assert "3" in repr_str

    def test_repr_empty_list(self, empty_list: DoublyLinkedList):
        assert repr(empty_list) == "DoublyLinkedList([])"


class TestTraversalIntegrityAfterOperations:
    def test_forward_traversal_links_consistent(self, empty_list: DoublyLinkedList):
        for i in range(10):
            empty_list.append(i)

        prev = None
        count = 0
        for node in empty_list.iterate_forward():
            assert node.prev is prev
            prev = node
            count += 1
        assert prev.next is None
        assert count == 10

    def test_backward_traversal_links_consistent(self, empty_list: DoublyLinkedList):
        for i in range(10):
            empty_list.append(i)

        nxt = None
        count = 0
        for node in empty_list.iterate_backward():
            assert node.next is nxt
            nxt = node
            count += 1
        assert nxt.prev is None
        assert count == 10

    def test_forward_backward_match_reversed(self, empty_list: DoublyLinkedList):
        data = ["a", "b", "c", "d", "e"]
        for d in data:
            empty_list.append(d)

        forward = empty_list.to_list_forward()
        backward = empty_list.to_list_backward()
        assert forward == data
        assert backward == list(reversed(data))

    def test_node_data_types(self, empty_list: DoublyLinkedList):
        empty_list.append(1)
        empty_list.append("string")
        empty_list.append({"key": "value"})
        empty_list.append([1, 2, 3])

        assert empty_list.size == 4
        result = empty_list.to_list_forward()
        assert result == [1, "string", {"key": "value"}, [1, 2, 3]]
