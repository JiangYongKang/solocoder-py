import pytest

from solocoder_py.doubly_linked_list import DoublyLinkedList


@pytest.fixture
def empty_list() -> DoublyLinkedList:
    return DoublyLinkedList()


@pytest.fixture
def single_node_list() -> DoublyLinkedList:
    dll = DoublyLinkedList()
    dll.append(1)
    return dll


@pytest.fixture
def three_node_list() -> DoublyLinkedList:
    dll = DoublyLinkedList()
    dll.append(1)
    dll.append(2)
    dll.append(3)
    return dll
