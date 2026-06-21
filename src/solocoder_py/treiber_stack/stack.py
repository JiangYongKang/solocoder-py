from dataclasses import dataclass
from threading import Lock
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class _Node(Generic[T]):
    value: T
    next: Optional["_Node[T]"] = None


@dataclass(frozen=True)
class _TaggedReference(Generic[T]):
    node: Optional[_Node[T]]
    version: int


class TreiberStack(Generic[T]):
    def __init__(self) -> None:
        self._head: _TaggedReference[T] = _TaggedReference(node=None, version=0)
        self._size: int = 0
        self._cas_lock: Lock = Lock()

    def _compare_and_swap(
        self,
        expected: _TaggedReference[T],
        new_ref: _TaggedReference[T],
        size_delta: int,
    ) -> bool:
        with self._cas_lock:
            if self._head is expected:
                self._head = new_ref
                self._size += size_delta
                return True
            return False

    def push(self, value: T) -> None:
        new_node = _Node(value=value)
        while True:
            current_head = self._head
            new_node.next = current_head.node
            new_ref = _TaggedReference(
                node=new_node, version=current_head.version + 1
            )
            if self._compare_and_swap(current_head, new_ref, 1):
                return

    def pop(self) -> Optional[T]:
        while True:
            current_head = self._head
            if current_head.node is None:
                return None
            next_node = current_head.node.next
            value = current_head.node.value
            new_ref = _TaggedReference(
                node=next_node, version=current_head.version + 1
            )
            if self._compare_and_swap(current_head, new_ref, -1):
                return value

    def peek(self) -> Optional[T]:
        current_head = self._head
        if current_head.node is None:
            return None
        return current_head.node.value

    def is_empty(self) -> bool:
        return self._head.node is None

    def size(self) -> int:
        return self._size

    def _get_version(self) -> int:
        return self._head.version
