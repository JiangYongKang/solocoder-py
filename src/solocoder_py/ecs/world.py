from __future__ import annotations

from typing import Any, Iterable, Iterator, TypeVar

from .archetype import ArchetypeManager
from .component import validate_component_type
from .entity import EntityId, EntityManager
from .exceptions import (
    ComponentAlreadyExistsError,
    ComponentNotFoundError,
    EntityNotFoundError,
)
from .sparse_set import SparseSet

C = TypeVar("C")


class World:
    def __init__(self) -> None:
        self._entities = EntityManager()
        self._components: dict[type, SparseSet] = {}
        self._archetypes = ArchetypeManager()
        self._entity_components: dict[int, dict[type, Any]] = {}

    def create_entity(self) -> EntityId:
        entity = self._entities.create()
        self._entity_components[entity.id] = {}
        return entity

    def destroy_entity(self, entity: EntityId) -> None:
        if not self._entities.is_alive(entity):
            raise EntityNotFoundError(entity.id)

        entity_id = entity.id

        for ct, ss in self._components.items():
            if ss.contains(entity):
                ss.remove(entity)

        self._archetypes.remove_entity(entity)

        self._entity_components.pop(entity_id, None)
        self._entities.destroy(entity)

    def is_entity_alive(self, entity: EntityId) -> bool:
        return self._entities.is_alive(entity)

    def entity_count(self) -> int:
        return self._entities.count()

    def add_component(self, entity: EntityId, component: Any) -> None:
        if not self._entities.is_alive(entity):
            raise EntityNotFoundError(entity.id)

        component_type = type(component)
        validate_component_type(component_type)

        if component_type not in self._components:
            self._components[component_type] = SparseSet(component_type)

        ss = self._components[component_type]
        if ss.contains(entity):
            raise ComponentAlreadyExistsError(entity.id, component_type)

        ss.insert(entity)

        self._entity_components[entity.id][component_type] = component

        self._update_archetype(entity)

    def remove_component(self, entity: EntityId, component_type: type[C]) -> None:
        if not self._entities.is_alive(entity):
            raise EntityNotFoundError(entity.id)

        validate_component_type(component_type)

        ss = self._components.get(component_type)
        if ss is None or not ss.contains(entity):
            raise ComponentNotFoundError(entity.id, component_type)

        ss.remove(entity)

        self._entity_components[entity.id].pop(component_type, None)

        self._update_archetype(entity)

    def get_component(
        self, entity: EntityId, component_type: type[C]
    ) -> C:
        if not self._entities.is_alive(entity):
            raise EntityNotFoundError(entity.id)

        validate_component_type(component_type)

        archetype = self._archetypes.get_entity_archetype(entity)
        if archetype is not None and component_type in archetype.component_types:
            return archetype.get_component(entity, component_type)

        raise ComponentNotFoundError(entity.id, component_type)

    def has_component(self, entity: EntityId, component_type: type) -> bool:
        if not self._entities.is_alive(entity):
            return False

        ss = self._components.get(component_type)
        if ss is None:
            return False

        return ss.contains(entity)

    def get_entity_components(self, entity: EntityId) -> dict[type, Any]:
        if not self._entities.is_alive(entity):
            raise EntityNotFoundError(entity.id)
        return dict(self._entity_components.get(entity.id, {}))

    def _update_archetype(self, entity: EntityId) -> None:
        entity_id = entity.id
        components = self._entity_components.get(entity_id, {})
        component_types = frozenset(components.keys())

        self._archetypes.migrate_entity(entity, component_types, components)

    def query_entities(
        self, component_types: Iterable[type]
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        types_list = tuple(component_types)
        for ct in types_list:
            validate_component_type(ct)

        if not types_list:
            return

        required = frozenset(types_list)
        matching_archetypes = self._archetypes.find_matching(required)

        for arch in matching_archetypes:
            yield from arch.iter_with_components(types_list)

    def query_entities_archetype(
        self, component_types: Iterable[type]
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        types_list = tuple(component_types)
        for ct in types_list:
            validate_component_type(ct)

        if not types_list:
            return

        required = frozenset(types_list)
        matching_archetypes = self._archetypes.find_matching(required)

        for arch in matching_archetypes:
            yield from arch.iter_with_components(types_list)

    def get_entities_with_component(
        self, component_type: type
    ) -> Iterator[EntityId]:
        validate_component_type(component_type)
        ss = self._components.get(component_type)
        if ss is None:
            return
        yield from ss.iter_entities()

    def iter_entities(self) -> Iterator[EntityId]:
        return self._entities.iter_entities()

    def get_entity_archetype(self, entity: EntityId) -> frozenset[type] | None:
        arch = self._archetypes.get_entity_archetype(entity)
        if arch is None:
            return None
        return arch.component_types

    def count_archetypes(self) -> int:
        return self._archetypes.count_archetypes()

    def clear(self) -> None:
        self._entities.clear()
        for ss in self._components.values():
            ss.clear()
        self._components.clear()
        self._archetypes.clear()
        self._entity_components.clear()
