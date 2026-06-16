from __future__ import annotations


class ECSError(Exception):
    pass


class EntityNotFoundError(ECSError):
    def __init__(self, entity_id: int) -> None:
        self.entity_id = entity_id
        super().__init__(f"Entity {entity_id} not found")


class EntityAlreadyExistsError(ECSError):
    def __init__(self, entity_id: int) -> None:
        self.entity_id = entity_id
        super().__init__(f"Entity {entity_id} already exists")


class ComponentNotFoundError(ECSError):
    def __init__(self, entity_id: int, component_type: type) -> None:
        self.entity_id = entity_id
        self.component_type = component_type
        super().__init__(
            f"Component {component_type.__name__} not found on entity {entity_id}"
        )


class ComponentAlreadyExistsError(ECSError):
    def __init__(self, entity_id: int, component_type: type) -> None:
        self.entity_id = entity_id
        self.component_type = component_type
        super().__init__(
            f"Component {component_type.__name__} already exists on entity {entity_id}"
        )


class SystemNotFoundError(ECSError):
    def __init__(self, system_name: str) -> None:
        self.system_name = system_name
        super().__init__(f"System {system_name} not found")


class SystemAlreadyExistsError(ECSError):
    def __init__(self, system_name: str) -> None:
        self.system_name = system_name
        super().__init__(f"System {system_name} already exists")


class CircularDependencyError(ECSError):
    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(
            f"Circular dependency detected in system scheduling: {' -> '.join(cycle)}"
        )


class ArchetypeNotFoundError(ECSError):
    def __init__(self, component_types: frozenset[type]) -> None:
        self.component_types = component_types
        names = ", ".join(t.__name__ for t in component_types)
        super().__init__(f"Archetype with components [{names}] not found")


class InvalidComponentError(ECSError):
    def __init__(self, component_type: type) -> None:
        self.component_type = component_type
        super().__init__(
            f"Invalid component type: {component_type.__name__}. "
            f"Components must be dataclasses with the @component decorator."
        )
