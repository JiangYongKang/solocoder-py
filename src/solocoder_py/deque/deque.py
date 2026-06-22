from __future__ import annotations

from typing import Any, Iterator, List

from .models import DequeEmptyError, DequeIndexError


class Deque:
    def __init__(self) -> None:
        self._items: List[Any] = []

    def add_front(self, item: Any) -> None:
        self._items.insert(0, item)

    def add_rear(self, item: Any) -> None:
        self._items.append(item)

    def remove_front(self) -> Any:
        if self.is_empty():
            raise DequeEmptyError("Cannot remove from an empty deque")
        return self._items.pop(0)

    def remove_rear(self) -> Any:
        if self.is_empty():
            raise DequeEmptyError("Cannot remove from an empty deque")
        return self._items.pop()

    def peek_front(self) -> Any:
        if self.is_empty():
            raise DequeEmptyError("Cannot peek from an empty deque")
        return self._items[0]

    def peek_rear(self) -> Any:
        if self.is_empty():
            raise DequeEmptyError("Cannot peek from an empty deque")
        return self._items[-1]

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def size(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> Any:
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if self.is_empty():
            raise DequeIndexError("Cannot access index on an empty deque")
        if index < 0 or index >= len(self._items):
            raise DequeIndexError(
                f"Index {index} out of range for deque of size {len(self._items)}"
            )
        return self._items[index]

    def __setitem__(self, index: int, value: Any) -> None:
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if self.is_empty():
            raise DequeIndexError("Cannot set index on an empty deque")
        if index < 0 or index >= len(self._items):
            raise DequeIndexError(
                f"Index {index} out of range for deque of size {len(self._items)}"
            )
        self._items[index] = value

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)

    def __contains__(self, item: Any) -> bool:
        return item in self._items

    def __repr__(self) -> str:
        return f"Deque({self._items})"

    def __str__(self) -> str:
        return str(self._items)

    def clear(self) -> None:
        self._items.clear()
