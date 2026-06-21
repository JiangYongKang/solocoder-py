from __future__ import annotations

import inspect
import typing
from typing import Any, Optional

from .exceptions import (
    CircularDependencyError,
    DependencyResolutionError,
    InvalidLifetimeError,
    ScopeDisposedError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)
from .models import Lifetime, ServiceDescriptor


class Scope:
    def __init__(self, container: "Container") -> None:
        self._container = container
        self._scoped_instances: dict[type, Any] = {}
        self._disposed = False

    def resolve(self, service_type: type) -> Any:
        if self._disposed:
            raise ScopeDisposedError()
        return self._container._resolve(service_type, self)

    def dispose(self) -> None:
        self._disposed = True
        self._scoped_instances.clear()

    def __enter__(self) -> "Scope":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.dispose()


class Container:
    def __init__(self) -> None:
        self._descriptors: dict[type, ServiceDescriptor] = {}
        self._singleton_instances: dict[type, Any] = {}

    def register(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> None:
        if not isinstance(lifetime, Lifetime):
            raise InvalidLifetimeError(lifetime)

        if service_type in self._descriptors:
            raise ServiceAlreadyRegisteredError(service_type)

        impl = implementation_type if implementation_type is not None else service_type

        self._descriptors[service_type] = ServiceDescriptor(
            service_type=service_type,
            implementation_type=impl,
            lifetime=lifetime,
        )

    def register_singleton(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
    ) -> None:
        self.register(service_type, implementation_type, Lifetime.SINGLETON)

    def register_transient(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
    ) -> None:
        self.register(service_type, implementation_type, Lifetime.TRANSIENT)

    def register_scoped(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
    ) -> None:
        self.register(service_type, implementation_type, Lifetime.SCOPED)

    def resolve(self, service_type: type) -> Any:
        return self._resolve(service_type, None)

    def create_scope(self) -> Scope:
        return Scope(self)

    def _resolve(
        self,
        service_type: type,
        scope: Optional[Scope],
        resolution_chain: Optional[list[type]] = None,
    ) -> Any:
        if resolution_chain is None:
            resolution_chain = []

        if service_type in resolution_chain:
            cycle = resolution_chain[resolution_chain.index(service_type):] + [service_type]
            raise CircularDependencyError(cycle)

        descriptor = self._descriptors.get(service_type)
        if descriptor is None:
            raise ServiceNotFoundError(service_type)

        if descriptor.lifetime == Lifetime.SINGLETON:
            if descriptor.instance is not None:
                return descriptor.instance
            resolution_chain.append(service_type)
            instance = self._create_instance(descriptor.implementation_type, scope, resolution_chain)
            descriptor.instance = instance
            return instance

        if descriptor.lifetime == Lifetime.SCOPED:
            if scope is None:
                scope = self._create_default_scope()
            if service_type in scope._scoped_instances:
                return scope._scoped_instances[service_type]
            resolution_chain.append(service_type)
            instance = self._create_instance(descriptor.implementation_type, scope, resolution_chain)
            scope._scoped_instances[service_type] = instance
            return instance

        resolution_chain.append(service_type)
        return self._create_instance(descriptor.implementation_type, scope, resolution_chain)

    def _create_instance(
        self,
        implementation_type: type,
        scope: Optional[Scope],
        resolution_chain: list[type],
    ) -> Any:
        if implementation_type.__init__ is object.__init__:
            return implementation_type()

        init_sig = inspect.signature(implementation_type.__init__)
        params = list(init_sig.parameters.values())

        if len(params) == 1 and params[0].name == "self":
            return implementation_type()

        module = inspect.getmodule(implementation_type)
        globalns = module.__dict__ if module is not None else {}
        localns = {}
        for cls in implementation_type.__mro__:
            localns[cls.__name__] = cls
        for descriptor in self._descriptors.values():
            localns[descriptor.service_type.__name__] = descriptor.service_type
            localns[descriptor.implementation_type.__name__] = descriptor.implementation_type

        try:
            type_hints = typing.get_type_hints(
                implementation_type.__init__,
                globalns=globalns,
                localns=localns,
            )
        except Exception:
            type_hints = {}

        constructor_args: dict[str, Any] = {}
        for param in params:
            if param.name == "self":
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            param_type = type_hints.get(param.name)
            if param_type is None:
                if param.annotation is not inspect.Parameter.empty:
                    raw_annotation = param.annotation
                    if isinstance(raw_annotation, str):
                        param_type = self._resolve_string_annotation(
                            raw_annotation, globalns, localns
                        )
            if not isinstance(param_type, type):
                raise DependencyResolutionError(
                    implementation_type, param.name
                )
            try:
                resolved = self._resolve(
                    param_type, scope, resolution_chain.copy()
                )
            except ServiceNotFoundError:
                raise DependencyResolutionError(
                    implementation_type, param.name
                )
            constructor_args[param.name] = resolved

        return implementation_type(**constructor_args)

    @staticmethod
    def _resolve_string_annotation(
        annotation: str, globalns: dict, localns: dict
    ) -> Optional[type]:
        try:
            return eval(annotation, globalns, localns)
        except Exception:
            return None

    def _create_default_scope(self) -> Scope:
        return Scope(self)
