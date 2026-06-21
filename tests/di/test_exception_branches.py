from __future__ import annotations

import pytest

from solocoder_py.di import (
    CircularDependencyError,
    Container,
    DependencyResolutionError,
    InvalidLifetimeError,
    ScopeDisposedError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)

from .conftest import Database, SimpleService


class TestDirectCircularDependency:
    def test_direct_circular_dependency_detected(self):
        container = Container()

        class ServiceA:
            def __init__(self, b: "ServiceB") -> None:
                self.b = b

        class ServiceB:
            def __init__(self, a: "ServiceA") -> None:
                self.a = a

        container.register(ServiceA)
        container.register(ServiceB)

        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(ServiceA)

        assert "ServiceA" in str(exc_info.value)
        assert "ServiceB" in str(exc_info.value)
        assert len(exc_info.value.cycle) >= 3


class TestIndirectCircularDependency:
    def test_indirect_circular_dependency_detected(self):
        container = Container()

        class ServiceA:
            def __init__(self, b: "ServiceB") -> None:
                self.b = b

        class ServiceB:
            def __init__(self, c: "ServiceC") -> None:
                self.c = c

        class ServiceC:
            def __init__(self, a: "ServiceA") -> None:
                self.a = a

        container.register(ServiceA)
        container.register(ServiceB)
        container.register(ServiceC)

        with pytest.raises(CircularDependencyError) as exc_info:
            container.resolve(ServiceA)

        cycle_names = [t.__name__ for t in exc_info.value.cycle]
        assert "ServiceA" in cycle_names
        assert "ServiceB" in cycle_names
        assert "ServiceC" in cycle_names


class TestServiceNotFound:
    def test_request_unregistered_type_raises_error(self, container):
        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.resolve(SimpleService)
        assert "SimpleService" in str(exc_info.value)
        assert exc_info.value.service_type is SimpleService

    def test_unregistered_dependency_in_chain_raises_error(self, container):
        class ServiceA:
            def __init__(self, b: "ServiceB") -> None:
                self.b = b

        class ServiceB:
            pass

        container.register(ServiceA)

        with pytest.raises(DependencyResolutionError) as exc_info:
            container.resolve(ServiceA)
        assert "ServiceA" in str(exc_info.value)
        assert "b" in str(exc_info.value)


class TestUnresolvableConstructorParameter:
    def test_parameter_without_annotation_raises_error(self, container):
        class BadService:
            def __init__(self, x) -> None:
                self.x = x

        container.register(BadService)

        with pytest.raises(DependencyResolutionError) as exc_info:
            container.resolve(BadService)
        assert "BadService" in str(exc_info.value)
        assert "x" in str(exc_info.value)

    def test_parameter_with_unregistered_type_annotation(self, container):
        class Dependent:
            def __init__(self, db: Database) -> None:
                self.db = db

        container.register(Dependent)

        with pytest.raises(DependencyResolutionError) as exc_info:
            container.resolve(Dependent)
        assert "Dependent" in str(exc_info.value)
        assert "db" in str(exc_info.value)


class TestScopeDisposed:
    def test_resolve_from_disposed_scope_raises_error(self, container):
        from .conftest import ScopedService

        container.register_scoped(ScopedService)
        scope = container.create_scope()
        scope.dispose()

        with pytest.raises(ScopeDisposedError):
            scope.resolve(ScopedService)


class TestInvalidLifetime:
    def test_invalid_lifetime_string_rejected(self, container):
        with pytest.raises(InvalidLifetimeError) as exc_info:
            container.register(SimpleService, lifetime="NOT_A_LIFETIME")
        assert "NOT_A_LIFETIME" in str(exc_info.value)

    def test_invalid_lifetime_none_rejected(self, container):
        with pytest.raises(InvalidLifetimeError):
            container.register(SimpleService, lifetime=None)

    def test_invalid_lifetime_number_rejected(self, container):
        with pytest.raises(InvalidLifetimeError):
            container.register(SimpleService, lifetime=42)


class TestDuplicateRegistration:
    def test_singleton_duplicate_registration_rejected(self, container):
        container.register_singleton(SimpleService)
        with pytest.raises(ServiceAlreadyRegisteredError) as exc_info:
            container.register_singleton(SimpleService)
        assert "SimpleService" in str(exc_info.value)

    def test_same_type_different_lifetime_rejected(self, container):
        container.register_singleton(SimpleService)
        with pytest.raises(ServiceAlreadyRegisteredError):
            container.register_transient(SimpleService)

    def test_duplicate_interface_registration_rejected(self, container):
        from .conftest import INotifier, EmailNotifier, SmsNotifier

        container.register(INotifier, EmailNotifier)
        with pytest.raises(ServiceAlreadyRegisteredError):
            container.register(INotifier, SmsNotifier)
