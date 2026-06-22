from __future__ import annotations

from typing import Any, List, Optional, Tuple

from .exceptions import HeapEmptyError
from .models import SupportsLessThan, HeapEntry


class BinaryHeap:
    def __init__(self, items: Optional[List[Tuple[SupportsLessThan, Any]]] = None) -> None:
        self._heap: List[HeapEntry] = []
        if items is not None:
            self.heapify(items)

    def insert(self, element: Any, priority: SupportsLessThan) -> None:
        entry = HeapEntry(priority=priority, element=element)
        self._heap.append(entry)
        self._bubble_up(len(self._heap) - 1)

    def extract_min(self) -> Any:
        if self.is_empty():
            raise HeapEmptyError("Cannot extract from an empty heap")

        min_entry = self._heap[0]
        last_entry = self._heap.pop()

        if not self.is_empty():
            self._heap[0] = last_entry
            self._bubble_down(0)

        return min_entry.element

    def peek_min(self) -> Any:
        if self.is_empty():
            raise HeapEmptyError("Cannot peek from an empty heap")
        return self._heap[0].element

    def heapify(self, items: List[Tuple[SupportsLessThan, Any]]) -> None:
        self._heap = [HeapEntry(priority=p, element=e) for p, e in items]
        n = len(self._heap)
        for i in range(n // 2 - 1, -1, -1):
            self._bubble_down(i)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def size(self) -> int:
        return len(self._heap)

    def _bubble_up(self, index: int) -> None:
        while index > 0:
            parent_index = (index - 1) // 2
            if self._heap[index].priority < self._heap[parent_index].priority:
                self._heap[index], self._heap[parent_index] = (
                    self._heap[parent_index],
                    self._heap[index],
                )
                index = parent_index
            else:
                break

    def _bubble_down(self, index: int) -> None:
        n = len(self._heap)
        while True:
            left_child_index = 2 * index + 1
            right_child_index = 2 * index + 2
            smallest_index = index

            if (
                left_child_index < n
                and self._heap[left_child_index].priority < self._heap[smallest_index].priority
            ):
                smallest_index = left_child_index

            if (
                right_child_index < n
                and self._heap[right_child_index].priority < self._heap[smallest_index].priority
            ):
                smallest_index = right_child_index

            if smallest_index != index:
                self._heap[index], self._heap[smallest_index] = (
                    self._heap[smallest_index],
                    self._heap[index],
                )
                index = smallest_index
            else:
                break
