from collections import deque
from typing import Generic, TypeVar

from .exceptions import QueueEmptyException

T = TypeVar("T")


class BasicQueue(Generic[T]):
    def __init__(self) -> None:
        self._items: deque[T] = deque()

    def enqueue(self, item: T) -> None:
        self._items.append(item)

    def dequeue(self) -> T:
        if self.is_empty():
            raise QueueEmptyException("Cannot dequeue from empty queue")
        return self._items.popleft()

    def peek(self) -> T:
        if self.is_empty():
            raise QueueEmptyException("Cannot peek at empty queue")
        return self._items[0]

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def size(self) -> int:
        return len(self._items)
