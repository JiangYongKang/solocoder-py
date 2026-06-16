from __future__ import annotations

from typing import Any, Iterator

from .entity import EntityId


class SparseSet:
    def __init__(self, component_type: type) -> None:
        self._component_type = component_type
        self._sparse: list[int] = []
        self._dense: list[int] = []

    def _ensure_sparse_capacity(self, entity_id: int) -> None:
        required_size = entity_id + 1
        if len(self._sparse) < required_size:
            self._sparse.extend([-1] * (required_size - len(self._sparse)))

    def insert(self, entity: EntityId) -> None:
        entity_id = entity.id
        self._ensure_sparse_capacity(entity_id)

        if self._sparse[entity_id] != -1:
            return

        dense_idx = len(self._dense)
        self._dense.append(entity_id)
        self._sparse[entity_id] = dense_idx

    def remove(self, entity: EntityId) -> None:
        entity_id = entity.id
        if entity_id >= len(self._sparse) or self._sparse[entity_id] == -1:
            return

        dense_idx = self._sparse[entity_id]
        last_dense_idx = len(self._dense) - 1

        if dense_idx != last_dense_idx:
            last_entity_id = self._dense[last_dense_idx]
            self._dense[dense_idx] = last_entity_id
            self._sparse[last_entity_id] = dense_idx

        self._dense.pop()
        self._sparse[entity_id] = -1

    def contains(self, entity: EntityId) -> bool:
        entity_id = entity.id
        return entity_id < len(self._sparse) and self._sparse[entity_id] != -1

    def iter_entities(self) -> Iterator[EntityId]:
        return (EntityId(eid) for eid in self._dense)

    def __len__(self) -> int:
        return len(self._dense)

    def __contains__(self, entity: EntityId) -> bool:
        return self.contains(entity)

    def clear(self) -> None:
        self._sparse.clear()
        self._dense.clear()

    @property
    def component_type(self) -> type:
        return self._component_type
