from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Set


@dataclass(frozen=True)
class Permission:
    action: str
    resource: str

    def __post_init__(self) -> None:
        if not self.action:
            raise ValueError("action cannot be empty")
        if not self.resource:
            raise ValueError("resource cannot be empty")

    @classmethod
    def parse(cls, spec: str) -> "Permission":
        if not spec:
            raise ValueError("permission spec cannot be empty")
        parts = spec.split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"invalid permission spec '{spec}', expected format 'action:resource'"
            )
        action, resource = parts
        return cls(action=action, resource=resource)

    def matches(self, action: str, resource: str) -> bool:
        return self.action == action and _match_pattern(self.resource, resource)

    def __str__(self) -> str:
        return f"{self.action}:{self.resource}"


def _match_pattern(pattern: str, value: str) -> bool:
    if pattern == "*":
        return True
    pattern_parts = pattern.split(":")
    value_parts = value.split(":")
    if len(pattern_parts) != len(value_parts):
        return False
    for p, v in zip(pattern_parts, value_parts):
        if p == "*":
            continue
        if p != v:
            return False
    return True


@dataclass
class Role:
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("role name cannot be empty")

    def add_permission(self, permission: Permission) -> None:
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission) -> None:
        self.permissions.discard(permission)

    def add_parent(self, parent_name: str) -> None:
        if not parent_name:
            raise ValueError("parent role name cannot be empty")
        if parent_name == self.name:
            raise ValueError("role cannot inherit from itself")
        self.parent_roles.add(parent_name)

    def remove_parent(self, parent_name: str) -> None:
        self.parent_roles.discard(parent_name)


@dataclass(frozen=True)
class UserRoleBinding:
    user_id: str
    role_names: FrozenSet[str]

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
