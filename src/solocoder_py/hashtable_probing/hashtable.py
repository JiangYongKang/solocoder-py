from __future__ import annotations

from typing import Any, Optional

from .exceptions import KeyNotFoundError
from .models import Entry

_DELETED = object()


class ProbingHashTable:
    def __init__(
        self,
        initial_capacity: int = 8,
        load_factor_threshold: float = 0.75,
    ) -> None:
        if initial_capacity <= 0:
            raise ValueError("initial_capacity must be positive")
        if not (0 < load_factor_threshold <= 1.0):
            raise ValueError("load_factor_threshold must be in (0, 1]")
        self._capacity = initial_capacity
        self._load_factor_threshold = load_factor_threshold
        self._slots: list[Any] = [None] * self._capacity
        self._count = 0
        self._deleted_count = 0

    def insert(self, key: Any, value: Any) -> None:
        index = self._hash(key)
        first_deleted: int = -1

        for _ in range(self._capacity):
            slot = self._slots[index]
            if slot is _DELETED:
                if first_deleted == -1:
                    first_deleted = index
            elif slot is not None:
                if slot.key == key:
                    slot.value = value
                    return
            else:
                break
            index = (index + 1) % self._capacity

        if self._count >= self._capacity:
            self._rehash(self._capacity * 2)
            self._insert_new(key, value)
        elif self._count + 1 >= int(self._capacity * self._load_factor_threshold):
            self._rehash(self._capacity * 2)
            self._insert_new(key, value)
        elif self._deleted_count >= self._count and self._deleted_count > 0:
            self._rehash(self._capacity)
            self._insert_new(key, value)
        else:
            target = first_deleted if first_deleted != -1 else index
            self._slots[target] = Entry(key=key, value=value)
            self._count += 1
            if first_deleted != -1:
                self._deleted_count -= 1

    def _insert_new(self, key: Any, value: Any) -> None:
        index = self._hash(key)
        while self._slots[index] is not None:
            index = (index + 1) % self._capacity
        self._slots[index] = Entry(key=key, value=value)
        self._count += 1

    def find(self, key: Any) -> Any:
        index = self._hash(key)
        for _ in range(self._capacity):
            slot = self._slots[index]
            if slot is None:
                break
            if slot is not _DELETED and slot.key == key:
                return slot.value
            index = (index + 1) % self._capacity
        raise KeyNotFoundError(f"Key not found: {key!r}")

    def delete(self, key: Any) -> Any:
        index = self._hash(key)
        for _ in range(self._capacity):
            slot = self._slots[index]
            if slot is None:
                break
            if slot is not _DELETED and slot.key == key:
                value = slot.value
                self._slots[index] = _DELETED
                self._count -= 1
                self._deleted_count += 1
                return value
            index = (index + 1) % self._capacity
        raise KeyNotFoundError(f"Key not found: {key!r}")

    def contains(self, key: Any) -> bool:
        try:
            self.find(key)
            return True
        except KeyNotFoundError:
            return False

    def size(self) -> int:
        return self._count

    def is_empty(self) -> bool:
        return self._count == 0

    def capacity(self) -> int:
        return self._capacity

    def load_factor(self) -> float:
        return self._count / self._capacity

    def deleted_count(self) -> int:
        return self._deleted_count

    def _hash(self, key: Any) -> int:
        return hash(key) % self._capacity

    def _rehash(self, new_capacity: int) -> None:
        old_slots = self._slots
        self._capacity = new_capacity
        self._slots = [None] * self._capacity
        self._count = 0
        self._deleted_count = 0
        for slot in old_slots:
            if slot is not None and slot is not _DELETED:
                index = self._hash(slot.key)
                while self._slots[index] is not None:
                    index = (index + 1) % self._capacity
                self._slots[index] = slot
                self._count += 1

    def __len__(self) -> int:
        return self._count

    def __contains__(self, key: Any) -> bool:
        return self.contains(key)

    def __repr__(self) -> str:
        pairs = []
        for slot in self._slots:
            if slot is not None and slot is not _DELETED:
                pairs.append(f"{slot.key!r}: {slot.value!r}")
        return f"ProbingHashTable({{{', '.join(pairs)}}})"
