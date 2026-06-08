from __future__ import annotations

import threading
import uuid
from typing import Any, Iterable, Optional

from .models import ORSetDiff, ORSetElement, ORSetState


class ORSet:
    def __init__(self, replica_id: Optional[str] = None) -> None:
        self._replica_id = replica_id or str(uuid.uuid4())
        self._elements: dict[Any, tuple[set[str], set[str]]] = {}
        self._lock = threading.RLock()

    @property
    def replica_id(self) -> str:
        return self._replica_id

    def _alive_tags(self, tags: set[str], tombstones: set[str]) -> set[str]:
        return tags - tombstones

    def add(self, element: Any) -> None:
        tag = f"{self._replica_id}-{uuid.uuid4()}"
        with self._lock:
            if element not in self._elements:
                self._elements[element] = (set(), set())
            tags, tombstones = self._elements[element]
            tags.add(tag)

    def add_all(self, elements: Iterable[Any]) -> None:
        for elem in elements:
            self.add(elem)

    def remove(self, element: Any) -> None:
        with self._lock:
            if element in self._elements:
                tags, tombstones = self._elements[element]
                alive = self._alive_tags(tags, tombstones)
                tombstones.update(alive)

    def contains(self, element: Any) -> bool:
        with self._lock:
            if element not in self._elements:
                return False
            tags, tombstones = self._elements[element]
            return bool(self._alive_tags(tags, tombstones))

    def value(self) -> set[Any]:
        with self._lock:
            result = set()
            for elem, (tags, tombstones) in self._elements.items():
                if self._alive_tags(tags, tombstones):
                    result.add(elem)
            return result

    def __contains__(self, element: Any) -> bool:
        return self.contains(element)

    def __len__(self) -> int:
        return len(self.value())

    def get_state(self) -> ORSetState:
        with self._lock:
            elements = {}
            for elem, (tags, tombstones) in self._elements.items():
                elements[elem] = ORSetElement(
                    tags=set(tags),
                    tombstones=set(tombstones),
                )
            return ORSetState(elements=elements)

    def merge(self, other: "ORSet") -> None:
        if not isinstance(other, ORSet):
            raise TypeError("can only merge with another ORSet")
        with self._lock:
            other_state = other.get_state()
            for elem, info in other_state.elements.items():
                if elem not in self._elements:
                    self._elements[elem] = (set(), set())
                tags, tombstones = self._elements[elem]
                tags.update(info.tags)
                tombstones.update(info.tombstones)

    def diff(self, other: "ORSet") -> ORSetDiff:
        if not isinstance(other, ORSet):
            raise TypeError("can only compute diff with another ORSet")
        with self._lock:
            self_state = self.get_state()
        other_state = other.get_state()

        added: dict[Any, set[str]] = {}
        removed: dict[Any, set[str]] = {}
        updated: dict[Any, tuple[set[str], set[str]]] = {}

        for elem, info in self_state.elements.items():
            self_alive = self._alive_tags(info.tags, info.tombstones)
            if elem not in other_state.elements:
                if self_alive:
                    added[elem] = set(self_alive)
            else:
                other_info = other_state.elements[elem]
                other_alive = self._alive_tags(other_info.tags, other_info.tombstones)
                if self_alive != other_alive:
                    updated[elem] = (set(other_alive), set(self_alive))

        for elem, info in other_state.elements.items():
            other_alive = self._alive_tags(info.tags, info.tombstones)
            if elem not in self_state.elements:
                if other_alive:
                    removed[elem] = set(other_alive)

        return ORSetDiff(
            added=added,
            removed=removed,
            updated=updated,
        )

    def is_ge(self, other: "ORSet") -> bool:
        if not isinstance(other, ORSet):
            raise TypeError("can only compare with another ORSet")
        with self._lock:
            self_state = self.get_state()
        other_state = other.get_state()

        for elem, info in other_state.elements.items():
            if elem not in self_state.elements:
                if info.tags:
                    return False
            else:
                self_info = self_state.elements[elem]
                if not info.tags.issubset(self_info.tags):
                    return False
                if not info.tombstones.issubset(self_info.tombstones):
                    return False
        return True

    def clear(self) -> None:
        with self._lock:
            for elem in list(self._elements.keys()):
                tags, tombstones = self._elements[elem]
                alive = self._alive_tags(tags, tombstones)
                tombstones.update(alive)
