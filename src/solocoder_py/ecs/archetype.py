from __future__ import annotations

from typing import Any, Iterator

from .component import validate_component_type
from .entity import EntityId


class Archetype:
    def __init__(self, component_types: frozenset[type]) -> None:
        for ct in component_types:
            validate_component_type(ct)

        self._component_types: frozenset[type] = component_types
        self._sorted_types: tuple[type, ...] = tuple(
            sorted(component_types, key=lambda t: t.__name__)
        )
        self._columns: dict[type, list[Any]] = {ct: [] for ct in component_types}
        self._entities: list[int] = []
        self._entity_to_row: dict[int, int] = {}

    @property
    def component_types(self) -> frozenset[type]:
        return self._component_types

    @property
    def sorted_types(self) -> tuple[type, ...]:
        return self._sorted_types

    def has_components(self, required: frozenset[type]) -> bool:
        return required.issubset(self._component_types)

    def count(self) -> int:
        return len(self._entities)

    def add_entity(self, entity: EntityId, components: dict[type, Any]) -> None:
        entity_id = entity.id
        row = len(self._entities)
        self._entities.append(entity_id)
        self._entity_to_row[entity_id] = row

        for ct in self._component_types:
            comp = components.get(ct)
            self._columns[ct].append(comp)

    def remove_entity(self, entity: EntityId) -> dict[type, Any]:
        entity_id = entity.id
        row = self._entity_to_row[entity_id]
        last_row = len(self._entities) - 1

        removed_components: dict[type, Any] = {}
        for ct in self._component_types:
            removed_components[ct] = self._columns[ct][row]

        if row != last_row:
            last_entity_id = self._entities[last_row]
            self._entities[row] = last_entity_id
            self._entity_to_row[last_entity_id] = row

            for ct in self._component_types:
                self._columns[ct][row] = self._columns[ct][last_row]

        self._entities.pop()
        for ct in self._component_types:
            self._columns[ct].pop()
        del self._entity_to_row[entity_id]

        return removed_components

    def get_component(self, entity: EntityId, component_type: type) -> Any:
        row = self._entity_to_row[entity.id]
        return self._columns[component_type][row]

    def set_component(self, entity: EntityId, component_type: type, value: Any) -> None:
        row = self._entity_to_row[entity.id]
        self._columns[component_type][row] = value

    def has_entity(self, entity: EntityId) -> bool:
        return entity.id in self._entity_to_row

    def iter_entities(self) -> Iterator[EntityId]:
        return (EntityId(eid) for eid in self._entities)

    def iter_column(self, component_type: type) -> Iterator[Any]:
        return iter(self._columns[component_type])

    def iter_columns(
        self, component_types: tuple[type, ...]
    ) -> Iterator[tuple[Any, ...]]:
        columns = [self._columns[ct] for ct in component_types]
        return zip(*columns)

    def iter_with_components(
        self, component_types: tuple[type, ...]
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        columns = [self._columns[ct] for ct in component_types]
        for entity_id, row_values in zip(self._entities, zip(*columns)):
            yield EntityId(entity_id), row_values

    def clear(self) -> None:
        self._entities.clear()
        self._entity_to_row.clear()
        for ct in self._component_types:
            self._columns[ct].clear()


class ArchetypeManager:
    def __init__(self) -> None:
        self._archetypes: dict[frozenset[type], Archetype] = {}
        self._entity_archetype: dict[int, Archetype] = {}
        self._entity_row: dict[int, int] = {}

    def get_or_create(self, component_types: frozenset[type]) -> Archetype:
        key = frozenset(component_types)
        if key not in self._archetypes:
            self._archetypes[key] = Archetype(key)
        return self._archetypes[key]

    def get(self, component_types: frozenset[type]) -> Archetype | None:
        return self._archetypes.get(frozenset(component_types))

    def get_entity_archetype(self, entity: EntityId) -> Archetype | None:
        return self._entity_archetype.get(entity.id)

    def set_entity_archetype(self, entity: EntityId, archetype: Archetype) -> None:
        self._entity_archetype[entity.id] = archetype

    def remove_entity_archetype(self, entity: EntityId) -> None:
        self._entity_archetype.pop(entity.id, None)

    def find_matching(self, required: frozenset[type]) -> list[Archetype]:
        return [
            arch for arch in self._archetypes.values() if arch.has_components(required)
        ]

    def count_archetypes(self) -> int:
        return sum(1 for arch in self._archetypes.values() if arch.count() > 0)

    def _cleanup_empty_archetypes(self) -> None:
        to_remove = [
            key for key, arch in self._archetypes.items() if arch.count() == 0
        ]
        for key in to_remove:
            del self._archetypes[key]

    def clear(self) -> None:
        for arch in self._archetypes.values():
            arch.clear()
        self._archetypes.clear()
        self._entity_archetype.clear()
        self._entity_row.clear()
