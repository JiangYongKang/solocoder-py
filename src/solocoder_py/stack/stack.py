from __future__ import annotations

from typing import Any, List

from .exceptions import StackEmptyError


class Stack:
    def __init__(self) -> None:
        self._items: List[Any] = []

    def push(self, item: Any) -> None:
        self._items.append(item)

    def pop(self) -> Any:
        if self.is_empty():
            raise StackEmptyError("Cannot pop from an empty stack")
        return self._items.pop()

    def peek(self) -> Any:
        if self.is_empty():
            raise StackEmptyError("Cannot peek at an empty stack")
        return self._items[-1]

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def size(self) -> int:
        return len(self._items)
