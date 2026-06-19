from __future__ import annotations


class HealthError(Exception):
    pass


class ComponentNotFoundError(HealthError):
    pass


class ComponentAlreadyRegisteredError(HealthError):
    pass


class CircularDependencyError(HealthError):
    pass


class InvalidComponentConfigError(HealthError):
    pass
