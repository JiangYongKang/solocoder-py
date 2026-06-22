from __future__ import annotations

from typing import Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class _Node(Generic[K, V]):
    __slots__ = ("key", "value", "next")

    def __init__(self, key: K, value: V, next: Optional["_Node[K, V]"] = None) -> None:
        self.key = key
        self.value = value
        self.next = next


class HashTable(Generic[K, V]):
    DEFAULT_INITIAL_CAPACITY = 8
    DEFAULT_LOAD_FACTOR_THRESHOLD = 0.75

    def __init__(
        self,
        initial_capacity: int = DEFAULT_INITIAL_CAPACITY,
        load_factor_threshold: float = DEFAULT_LOAD_FACTOR_THRESHOLD,
    ) -> None:
        if initial_capacity <= 0:
            raise ValueError("initial_capacity must be positive")
        if load_factor_threshold <= 0 or load_factor_threshold > 1:
            raise ValueError("load_factor_threshold must be in (0, 1]")

        self._capacity = initial_capacity
        self._load_factor_threshold = load_factor_threshold
        self._size = 0
        self._buckets: list[Optional[_Node[K, V]]] = [None] * initial_capacity

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def load_factor_threshold(self) -> float:
        return self._load_factor_threshold

    def size(self) -> int:
        return self._size

    def load_factor(self) -> float:
        if self._capacity == 0:
            return 0.0
        return self._size / self._capacity

    def put(self, key: K, value: V) -> None:
        index = self._hash(key)

        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        new_node = _Node(key, value, self._buckets[index])
        self._buckets[index] = new_node
        self._size += 1

        if self.load_factor() > self._load_factor_threshold:
            self._resize()

    def get(self, key: K) -> V:
        index = self._hash(key)

        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next

        raise KeyError(key)

    def remove(self, key: K) -> V:
        index = self._hash(key)

        prev = None
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                if prev is None:
                    self._buckets[index] = node.next
                else:
                    prev.next = node.next
                self._size -= 1
                return node.value
            prev = node
            node = node.next

        raise KeyError(key)

    def contains(self, key: K) -> bool:
        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def __getitem__(self, key: K) -> V:
        return self.get(key)

    def __setitem__(self, key: K, value: V) -> None:
        self.put(key, value)

    def __len__(self) -> int:
        return self._size

    def _hash(self, key: K) -> int:
        return hash(key) % self._capacity

    def _resize(self) -> None:
        new_capacity = self._capacity * 2
        new_buckets: list[Optional[_Node[K, V]]] = [None] * new_capacity

        for i in range(self._capacity):
            node = self._buckets[i]
            while node is not None:
                next_node = node.next
                new_index = hash(node.key) % new_capacity
                node.next = new_buckets[new_index]
                new_buckets[new_index] = node
                node = next_node

        self._capacity = new_capacity
        self._buckets = new_buckets
