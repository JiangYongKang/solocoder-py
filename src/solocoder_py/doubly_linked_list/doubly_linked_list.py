from __future__ import annotations

from typing import Any, Iterator, List, Optional

from .models import Node, NodeNotFoundError


class DoublyLinkedList:
    def __init__(self) -> None:
        self._head: Optional[Node] = None
        self._tail: Optional[Node] = None
        self._size: int = 0

    @property
    def head(self) -> Optional[Node]:
        return self._head

    @property
    def tail(self) -> Optional[Node]:
        return self._tail

    @property
    def size(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0

    def prepend(self, data: Any) -> Node:
        new_node = Node(data=data)
        if self._head is None:
            self._head = new_node
            self._tail = new_node
        else:
            new_node.next = self._head
            self._head.prev = new_node
            self._head = new_node
        self._size += 1
        return new_node

    def append(self, data: Any) -> Node:
        new_node = Node(data=data)
        if self._tail is None:
            self._head = new_node
            self._tail = new_node
        else:
            new_node.prev = self._tail
            self._tail.next = new_node
            self._tail = new_node
        self._size += 1
        return new_node

    def insert_after(self, existing_node: Node, data: Any) -> Node:
        if existing_node is None:
            raise NodeNotFoundError("Cannot insert after None node")

        if not self._contains_node(existing_node):
            raise NodeNotFoundError("Node does not belong to this list")

        new_node = Node(data=data)
        new_node.prev = existing_node
        new_node.next = existing_node.next

        if existing_node.next is None:
            self._tail = new_node
        else:
            existing_node.next.prev = new_node

        existing_node.next = new_node
        self._size += 1
        return new_node

    def delete_node(self, node: Node) -> bool:
        if node is None:
            return False

        if not self._contains_node(node):
            return False

        prev_node = node.prev
        next_node = node.next

        if prev_node is None:
            self._head = next_node
        else:
            prev_node.next = next_node

        if next_node is None:
            self._tail = prev_node
        else:
            next_node.prev = prev_node

        node.prev = None
        node.next = None
        self._size -= 1
        return True

    def delete_head(self) -> bool:
        if self._head is None:
            return False
        return self.delete_node(self._head)

    def delete_tail(self) -> bool:
        if self._tail is None:
            return False
        return self.delete_node(self._tail)

    def reverse(self) -> None:
        if self._size <= 1:
            return

        current = self._head
        new_head = self._tail
        new_tail = self._head

        while current is not None:
            next_node = current.next
            current.next = current.prev
            current.prev = next_node
            current = next_node

        self._head = new_head
        self._tail = new_tail

    def iterate_forward(self) -> Iterator[Node]:
        current = self._head
        while current is not None:
            yield current
            current = current.next

    def iterate_backward(self) -> Iterator[Node]:
        current = self._tail
        while current is not None:
            yield current
            current = current.prev

    def to_list_forward(self) -> List[Any]:
        return [node.data for node in self.iterate_forward()]

    def to_list_backward(self) -> List[Any]:
        return [node.data for node in self.iterate_backward()]

    def find(self, data: Any) -> Optional[Node]:
        for node in self.iterate_forward():
            if node.data == data:
                return node
        return None

    def _contains_node(self, node: Node) -> bool:
        if self._head is None:
            return False

        current = self._head
        while current is not None:
            if current is node:
                return True
            current = current.next
        return False

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[Node]:
        return self.iterate_forward()

    def __repr__(self) -> str:
        data_list = self.to_list_forward()
        return f"DoublyLinkedList({data_list!r})"
