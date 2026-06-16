from __future__ import annotations

from typing import Any, Iterator, TYPE_CHECKING

from .entity import EntityId

if TYPE_CHECKING:
    from .archetype import ArchetypeManager


class SparseSet:
    def __init__(self, component_type: type, archetype_manager: ArchetypeManager | None = None) -> None:
        self._component_type = component_type
        self._sparse: list[int] = []
        self._dense: list[int] = []
        self._archetype_manager = archetype_manager

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

    def get(self, entity: EntityId) -> Any:
        if not self.contains(entity):
            return None
        if self._archetype_manager is None:
            raise RuntimeError("SparseSet not initialized with ArchetypeManager for data access")
        archetype = self._archetype_manager.get_entity_archetype(entity)
        if archetype is None:
            return None
        return archetype.get_component(entity, self._component_type)

    def iter_entities(self) -> Iterator[EntityId]:
        return (EntityId(eid) for eid in self._dense)

    def iter_components(self) -> Iterator[Any]:
        if self._archetype_manager is None:
            raise RuntimeError("SparseSet not initialized with ArchetypeManager for data access")
        for entity_id in self._dense:
            entity = EntityId(entity_id)
            archetype = self._archetype_manager.get_entity_archetype(entity)
            if archetype is not None:
                yield archetype.get_component(entity, self._component_type)

    def iter(self) -> Iterator[tuple[EntityId, Any]]:
        if self._archetype_manager is None:
            raise RuntimeError("SparseSet not initialized with ArchetypeManager for data access")
        for entity_id in self._dense:
            entity = EntityId(entity_id)
            archetype = self._archetype_manager.get_entity_archetype(entity)
            if archetype is not None:
                yield entity, archetype.get_component(entity, self._component_type)

    def __getitem__(self, entity: EntityId) -> Any:
        if not self.contains(entity):
            raise KeyError(entity.id)
        value = self.get(entity)
        if value is None:
            raise KeyError(entity.id)
        return value

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

    def set_archetype_manager(self, archetype_manager: ArchetypeManager) -> None:
        self._archetype_manager = archetype_manager
