from __future__ import annotations

from typing import Iterator

from .exceptions import EntityAlreadyExistsError, EntityNotFoundError


class EntityId:
    def __init__(self, id: int) -> None:
        self.id = id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EntityId):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"EntityId({self.id})"

    def __int__(self) -> int:
        return self.id


class EntityManager:
    def __init__(self) -> None:
        self._next_id: int = 0
        self._active: set[int] = set()
        self._free_list: list[int] = []

    def create(self) -> EntityId:
        if self._free_list:
            entity_id = self._free_list.pop()
        else:
            entity_id = self._next_id
            self._next_id += 1

        if entity_id in self._active:
            raise EntityAlreadyExistsError(entity_id)

        self._active.add(entity_id)
        return EntityId(entity_id)

    def destroy(self, entity: EntityId) -> None:
        entity_id = entity.id
        if entity_id not in self._active:
            raise EntityNotFoundError(entity_id)

        self._active.remove(entity_id)
        self._free_list.append(entity_id)

    def is_alive(self, entity: EntityId) -> bool:
        return entity.id in self._active

    def count(self) -> int:
        return len(self._active)

    def iter_entities(self) -> Iterator[EntityId]:
        return (EntityId(eid) for eid in self._active)

    def clear(self) -> None:
        self._active.clear()
        self._free_list.clear()
        self._next_id = 0
