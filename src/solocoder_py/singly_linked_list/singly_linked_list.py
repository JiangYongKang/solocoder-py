from __future__ import annotations

from typing import Any, List, Optional

from .models import Node, NodeNotFoundError


class SinglyLinkedList:
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

    def is_empty(self) -> bool:
        return self._size == 0

    def size(self) -> int:
        return self._size

    def __len__(self) -> int:
        return self._size

    def prepend(self, value: Any) -> Node:
        new_node = Node(value=value)
        if self._head is None:
            self._head = new_node
            self._tail = new_node
        else:
            new_node.next = self._head
            self._head = new_node
        self._size += 1
        return new_node

    def append(self, value: Any) -> Node:
        new_node = Node(value=value)
        if self._tail is None:
            self._head = new_node
            self._tail = new_node
        else:
            self._tail.next = new_node
            self._tail = new_node
        self._size += 1
        return new_node

    def find(self, value: Any) -> Optional[Node]:
        current = self._head
        while current is not None:
            if current.value == value:
                return current
            current = current.next
        return None

    def remove(self, value: Any) -> bool:
        if self._head is None:
            return False

        if self._head.value == value:
            removed_node = self._head
            self._head = self._head.next
            if self._head is None:
                self._tail = None
            removed_node.next = None
            self._size -= 1
            return True

        prev = self._head
        current = self._head.next
        while current is not None:
            if current.value == value:
                prev.next = current.next
                if current is self._tail:
                    self._tail = prev
                current.next = None
                self._size -= 1
                return True
            prev = current
            current = current.next

        return False

    def reverse(self) -> None:
        if self._head is None or self._head.next is None:
            return

        prev = None
        current = self._head
        self._tail = self._head

        while current is not None:
            next_node = current.next
            current.next = prev
            prev = current
            current = next_node

        self._head = prev

    def traverse(self) -> List[Any]:
        result: List[Any] = []
        current = self._head
        while current is not None:
            result.append(current.value)
            current = current.next
        return result

    def __iter__(self):
        current = self._head
        while current is not None:
            yield current.value
            current = current.next

    def __repr__(self) -> str:
        values = " -> ".join(repr(v) for v in self.traverse())
        return f"SinglyLinkedList([{values}])"
