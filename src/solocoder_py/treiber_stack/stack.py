from dataclasses import dataclass
from threading import Lock
from typing import Generic, Optional, TypeVar, Tuple

T = TypeVar("T")


@dataclass
class _Node(Generic[T]):
    value: T
    next: Optional["_Node[T]"] = None


@dataclass(frozen=True)
class _TaggedReference(Generic[T]):
    node: Optional[_Node[T]]
    version: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _TaggedReference):
            return False
        return self.node is other.node and self.version == other.version


class TreiberStack(Generic[T]):
    def __init__(self) -> None:
        self._head: _TaggedReference[T] = _TaggedReference(node=None, version=0)
        self._cas_lock = Lock()
        self._size_lock = Lock()
        self._size: int = 0

    def _compare_and_swap(
        self,
        expected: _TaggedReference[T],
        new_node: Optional[_Node[T]],
    ) -> bool:
        with self._cas_lock:
            if self._head == expected:
                self._head = _TaggedReference(node=new_node, version=expected.version + 1)
                return True
            return False

    def _increment_size(self) -> None:
        with self._size_lock:
            self._size += 1

    def _decrement_size(self) -> None:
        with self._size_lock:
            self._size -= 1

    def push(self, value: T) -> None:
        new_node = _Node(value=value)
        while True:
            current_head = self._head
            new_node.next = current_head.node
            if self._compare_and_swap(current_head, new_node):
                self._increment_size()
                return

    def pop(self) -> Optional[T]:
        while True:
            current_head = self._head
            if current_head.node is None:
                return None
            next_node = current_head.node.next
            if self._compare_and_swap(current_head, next_node):
                self._decrement_size()
                return current_head.node.value

    def peek(self) -> Optional[T]:
        current_head = self._head
        if current_head.node is None:
            return None
        return current_head.node.value

    def is_empty(self) -> bool:
        return self._head.node is None

    def size(self) -> int:
        with self._size_lock:
            return self._size

    def _get_version(self) -> int:
        return self._head.version
