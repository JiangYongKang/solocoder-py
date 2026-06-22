import pytest

from solocoder_py.singly_linked_list import SinglyLinkedList


@pytest.fixture
def linked_list() -> SinglyLinkedList:
    return SinglyLinkedList()


@pytest.fixture
def filled_list() -> SinglyLinkedList:
    ll = SinglyLinkedList()
    ll.append(1)
    ll.append(2)
    ll.append(3)
    ll.append(4)
    ll.append(5)
    return ll
