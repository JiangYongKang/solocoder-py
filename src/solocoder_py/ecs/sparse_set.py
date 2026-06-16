from __future__ import annotations

from typing import Any, Iterator, TypeVar

from .entity import EntityId

T = TypeVar("T")


class SparseSet:
    def __init__(self, component_type: type) -> None:
        self._component_type = component_type
        self._sparse: list[int] = []
        self._dense: list[int] = []
        self._components: list[Any] = []

    def _ensure_sparse_capacity(self, entity_id: int) -> None:
        required_size = entity_id + 1
        if len(self._sparse) < required_size:
            self._sparse.extend([-1] * (required_size - len(self._sparse)))

    def insert(self, entity: EntityId, component: Any) -> None:
        entity_id = entity.id
        self._ensure_sparse_capacity(entity_id)

        if self._sparse[entity_id] != -1:
            dense_idx = self._sparse[entity_id]
            self._components[dense_idx] = component
            return

        dense_idx = len(self._dense)
        self._dense.append(entity_id)
        self._components.append(component)
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
            self._components[dense_idx] = self._components[last_dense_idx]
            self._sparse[last_entity_id] = dense_idx

        self._dense.pop()
        self._components.pop()
        self._sparse[entity_id] = -1

    def contains(self, entity: EntityId) -> bool:
        entity_id = entity.id
        return entity_id < len(self._sparse) and self._sparse[entity_id] != -1

    def get(self, entity: EntityId) -> Any:
        entity_id = entity.id
        if entity_id >= len(self._sparse) or self._sparse[entity_id] == -1:
            return None
        dense_idx = self._sparse[entity_id]
        return self._components[dense_idx]

    def iter_entities(self) -> Iterator[EntityId]:
        return (EntityId(eid) for eid in self._dense)

    def iter_components(self) -> Iterator[Any]:
        return iter(self._components)

    def iter(self) -> Iterator[tuple[EntityId, Any]]:
        return ((EntityId(eid), comp) for eid, comp in zip(self._dense, self._components))

    def __len__(self) -> int:
        return len(self._dense)

    def __contains__(self, entity: EntityId) -> bool:
        return self.contains(entity)

    def __getitem__(self, entity: EntityId) -> Any:
        result = self.get(entity)
        if result is None:
            raise KeyError(entity)
        return result

    def clear(self) -> None:
        self._sparse.clear()
        self._dense.clear()
        self._components.clear()

    @property
    def component_type(self) -> type:
        return self._component_type
