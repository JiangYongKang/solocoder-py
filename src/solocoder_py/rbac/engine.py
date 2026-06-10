from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set

from .exceptions import (
    CircularInheritanceError,
    PermissionNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
)
from .models import Permission, Role, UserRoleBinding


@dataclass
class RBACEngine:
    _roles: Dict[str, Role] = field(default_factory=dict)
    _user_bindings: Dict[str, UserRoleBinding] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def create_role(self, name: str) -> Role:
        if not name:
            raise ValueError("role name cannot be empty")
        with self._lock:
            if name in self._roles:
                raise RoleAlreadyExistsError(f"role '{name}' already exists")
            role = Role(name=name)
            self._roles[name] = role
            return role

    def get_role(self, name: str) -> Role:
        if not name:
            raise ValueError("role name cannot be empty")
        with self._lock:
            role = self._roles.get(name)
            if role is None:
                raise RoleNotFoundError(f"role '{name}' not found")
            return role

    def delete_role(self, name: str) -> bool:
        if not name:
            raise ValueError("role name cannot be empty")
        with self._lock:
            if name not in self._roles:
                return False
            del self._roles[name]
            for role in self._roles.values():
                role.parent_roles.discard(name)
            for binding in list(self._user_bindings.values()):
                if name in binding.role_names:
                    new_names = set(binding.role_names)
                    new_names.discard(name)
                    self._user_bindings[binding.user_id] = UserRoleBinding(
                        user_id=binding.user_id,
                        role_names=frozenset(new_names),
                    )
            return True

    def list_roles(self) -> List[Role]:
        with self._lock:
            return [Role(name=r.name, permissions=set(r.permissions), parent_roles=set(r.parent_roles)) for r in self._roles.values()]

    def add_permission_to_role(self, role_name: str, permission: Permission) -> None:
        if not role_name:
            raise ValueError("role name cannot be empty")
        with self._lock:
            role = self._roles.get(role_name)
            if role is None:
                raise RoleNotFoundError(f"role '{role_name}' not found")
            role.add_permission(permission)

    def remove_permission_from_role(self, role_name: str, permission: Permission) -> None:
        if not role_name:
            raise ValueError("role name cannot be empty")
        with self._lock:
            role = self._roles.get(role_name)
            if role is None:
                raise RoleNotFoundError(f"role '{role_name}' not found")
            role.remove_permission(permission)

    def add_parent_role(self, role_name: str, parent_name: str) -> None:
        if not role_name:
            raise ValueError("role name cannot be empty")
        if not parent_name:
            raise ValueError("parent role name cannot be empty")
        with self._lock:
            if role_name not in self._roles:
                raise RoleNotFoundError(f"role '{role_name}' not found")
            if parent_name not in self._roles:
                raise RoleNotFoundError(f"role '{parent_name}' not found")
            if self._would_create_cycle(role_name, parent_name):
                raise CircularInheritanceError(
                    f"adding parent '{parent_name}' to role '{role_name}' would create a cycle"
                )
            self._roles[role_name].add_parent(parent_name)

    def remove_parent_role(self, role_name: str, parent_name: str) -> None:
        if not role_name:
            raise ValueError("role name cannot be empty")
        if not parent_name:
            raise ValueError("parent role name cannot be empty")
        with self._lock:
            if role_name not in self._roles:
                raise RoleNotFoundError(f"role '{role_name}' not found")
            self._roles[role_name].remove_parent(parent_name)

    def _would_create_cycle(self, role_name: str, new_parent_name: str) -> bool:
        visited: Set[str] = set()
        stack: List[str] = [new_parent_name]
        while stack:
            current = stack.pop()
            if current == role_name:
                return True
            if current in visited:
                continue
            visited.add(current)
            current_role = self._roles.get(current)
            if current_role is not None:
                stack.extend(current_role.parent_roles)
        return False

    def get_role_inheritance_chain(self, role_name: str) -> List[str]:
        if not role_name:
            raise ValueError("role name cannot be empty")
        with self._lock:
            if role_name not in self._roles:
                raise RoleNotFoundError(f"role '{role_name}' not found")
            chain: List[str] = []
            visited: Set[str] = set()
            self._collect_inheritance_chain(role_name, chain, visited)
            return chain

    def _collect_inheritance_chain(
        self, role_name: str, chain: List[str], visited: Set[str]
    ) -> None:
        if role_name in visited:
            return
        visited.add(role_name)
        chain.append(role_name)
        role = self._roles.get(role_name)
        if role is not None:
            for parent_name in role.parent_roles:
                self._collect_inheritance_chain(parent_name, chain, visited)

    def bind_user_to_roles(self, user_id: str, role_names: List[str]) -> None:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        with self._lock:
            for rn in role_names:
                if rn not in self._roles:
                    raise RoleNotFoundError(f"role '{rn}' not found")
            self._user_bindings[user_id] = UserRoleBinding(
                user_id=user_id, role_names=frozenset(role_names)
            )

    def unbind_user(self, user_id: str) -> bool:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        with self._lock:
            if user_id not in self._user_bindings:
                return False
            del self._user_bindings[user_id]
            return True

    def get_user_roles(self, user_id: str) -> FrozenSet[str]:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        with self._lock:
            binding = self._user_bindings.get(user_id)
            if binding is None:
                return frozenset()
            return frozenset(binding.role_names)

    def get_user_effective_roles(self, user_id: str) -> List[str]:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        with self._lock:
            binding = self._user_bindings.get(user_id)
            if binding is None:
                return []
            effective: List[str] = []
            visited: Set[str] = set()
            for role_name in binding.role_names:
                self._collect_inheritance_chain(role_name, effective, visited)
            return effective

    def get_role_effective_permissions(self, role_name: str) -> Set[Permission]:
        if not role_name:
            raise ValueError("role name cannot be empty")
        with self._lock:
            if role_name not in self._roles:
                raise RoleNotFoundError(f"role '{role_name}' not found")
            chain = self.get_role_inheritance_chain(role_name)
            permissions: Set[Permission] = set()
            for rn in chain:
                role = self._roles.get(rn)
                if role is not None:
                    permissions.update(role.permissions)
            return permissions

    def get_user_effective_permissions(self, user_id: str) -> Set[Permission]:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        with self._lock:
            effective_roles = self.get_user_effective_roles(user_id)
            permissions: Set[Permission] = set()
            for rn in effective_roles:
                role = self._roles.get(rn)
                if role is not None:
                    permissions.update(role.permissions)
            return permissions

    def check_permission(
        self, user_id: str, action: str, resource: str
    ) -> bool:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        if not action:
            raise ValueError("action cannot be empty")
        if not resource:
            raise ValueError("resource cannot be empty")
        with self._lock:
            effective_perms = self.get_user_effective_permissions(user_id)
            for perm in effective_perms:
                if perm.matches(action, resource):
                    return True
            return False

    def check_role_permission(
        self, role_name: str, action: str, resource: str
    ) -> bool:
        if not role_name:
            raise ValueError("role name cannot be empty")
        if not action:
            raise ValueError("action cannot be empty")
        if not resource:
            raise ValueError("resource cannot be empty")
        with self._lock:
            effective_perms = self.get_role_effective_permissions(role_name)
            for perm in effective_perms:
                if perm.matches(action, resource):
                    return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._roles.clear()
            self._user_bindings.clear()
