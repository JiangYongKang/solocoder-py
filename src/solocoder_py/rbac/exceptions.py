from __future__ import annotations


class RBACError(Exception):
    pass


class PermissionNotFoundError(RBACError):
    pass


class RoleNotFoundError(RBACError):
    pass


class RoleAlreadyExistsError(RBACError):
    pass


class PermissionAlreadyExistsError(RBACError):
    pass


class CircularInheritanceError(RBACError):
    pass
