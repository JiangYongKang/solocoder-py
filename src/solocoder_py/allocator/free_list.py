from __future__ import annotations

from typing import Generator, Optional

from .models import Block


class FreeListNode:
    __slots__ = ("block", "prev", "next")

    def __init__(self, block: Block) -> None:
        self.block = block
        self.prev: Optional[FreeListNode] = None
        self.next: Optional[FreeListNode] = None


class FreeList:
    def __init__(self) -> None:
        self.head: Optional[FreeListNode] = None
        self._count: int = 0

    @property
    def count(self) -> int:
        return self._count

    def insert_sorted(self, node: FreeListNode) -> None:
        node.prev = None
        node.next = None

        if self.head is None:
            self.head = node
            self._count += 1
            return

        current = self.head
        prev_node: Optional[FreeListNode] = None
        while current is not None and current.block.start < node.block.start:
            prev_node = current
            current = current.next

        if current is None:
            assert prev_node is not None
            prev_node.next = node
            node.prev = prev_node
        elif prev_node is None:
            node.next = self.head
            self.head.prev = node
            self.head = node
        else:
            prev_node.next = node
            node.prev = prev_node
            node.next = current
            current.prev = node

        self._count += 1

    def remove(self, node: FreeListNode) -> None:
        if node.prev is not None:
            node.prev.next = node.next
        else:
            self.head = node.next
        if node.next is not None:
            node.next.prev = node.prev
        node.prev = None
        node.next = None
        self._count -= 1

    def find_first_fit(self, size: int) -> Optional[FreeListNode]:
        current = self.head
        while current is not None:
            if current.block.size >= size:
                return current
            current = current.next
        return None

    def find_best_fit(self, size: int) -> Optional[FreeListNode]:
        best: Optional[FreeListNode] = None
        current = self.head
        while current is not None:
            if current.block.size >= size:
                if best is None:
                    best = current
                elif current.block.size < best.block.size:
                    best = current
                elif current.block.size == best.block.size and current.block.start > best.block.start:
                    best = current
            current = current.next
        return best

    def nodes(self) -> Generator[FreeListNode, None, None]:
        current = self.head
        while current is not None:
            yield current
            current = current.next

    def clear(self) -> None:
        current = self.head
        while current is not None:
            next_node = current.next
            current.prev = None
            current.next = None
            current = next_node
        self.head = None
        self._count = 0
