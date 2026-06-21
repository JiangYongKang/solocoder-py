from __future__ import annotations


class DIError(Exception):
    pass


class ServiceNotFoundError(DIError):
    def __init__(self, service_type: type) -> None:
        self.service_type = service_type
        super().__init__(
            f"Service not registered: {service_type.__name__}"
        )


class CircularDependencyError(DIError):
    def __init__(self, cycle: list[type]) -> None:
        self.cycle = cycle
        names = " -> ".join(t.__name__ for t in cycle)
        super().__init__(
            f"Circular dependency detected: {names}"
        )


class DependencyResolutionError(DIError):
    def __init__(self, service_type: type, param_name: str) -> None:
        self.service_type = service_type
        self.param_name = param_name
        super().__init__(
            f"Cannot resolve parameter '{param_name}' of {service_type.__name__}"
        )


class InvalidLifetimeError(DIError):
    def __init__(self, lifetime: object) -> None:
        self.lifetime = lifetime
        super().__init__(
            f"Invalid lifetime: {lifetime}. Must be a Lifetime enum value"
        )


class ServiceAlreadyRegisteredError(DIError):
    def __init__(self, service_type: type) -> None:
        self.service_type = service_type
        super().__init__(
            f"Service already registered: {service_type.__name__}"
        )


class ScopeDisposedError(DIError):
    def __init__(self) -> None:
        super().__init__("Cannot resolve services from a disposed scope")
