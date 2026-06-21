from __future__ import annotations

from solocoder_py.di import Container, Lifetime, ScopeDisposedError

from .conftest import (
    Database,
    Logger,
    Repository,
    ScopedService,
    ServiceWithCounter,
    SimpleService,
    SingletonService,
)


class TestNoConstructorParameters:
    def test_no_params_type_resolves_normally(self, container):
        class NoParams:
            pass

        container.register(NoParams)
        instance = container.resolve(NoParams)
        assert isinstance(instance, NoParams)

    def test_object_with_empty_init_resolves(self, container):
        class EmptyInit:
            def __init__(self) -> None:
                self.value = 42

        container.register(EmptyInit)
        instance = container.resolve(EmptyInit)
        assert isinstance(instance, EmptyInit)
        assert instance.value == 42


class TestSingletonConstructorOnce:
    def test_singleton_constructor_runs_only_once(self, container):
        ServiceWithCounter.call_count = 0
        container.register_singleton(ServiceWithCounter)
        for _ in range(10):
            container.resolve(ServiceWithCounter)
        assert ServiceWithCounter.call_count == 1

    def test_singleton_injected_as_dependency_uses_same_instance(self, container):
        ServiceWithCounter.call_count = 0
        container.register_singleton(ServiceWithCounter)

        class DependentA:
            def __init__(self, dep: ServiceWithCounter) -> None:
                self.dep = dep

        class DependentB:
            def __init__(self, dep: ServiceWithCounter) -> None:
                self.dep = dep

        container.register(DependentA)
        container.register(DependentB)
        a = container.resolve(DependentA)
        b = container.resolve(DependentB)
        assert a.dep is b.dep
        assert ServiceWithCounter.call_count == 1


class TestNestedScopeIsolation:
    def test_nested_scopes_have_isolated_scoped_instances(self, container):
        container.register_scoped(ScopedService)
        outer_scope = container.create_scope()
        inner_scope = container.create_scope()
        outer_instance = outer_scope.resolve(ScopedService)
        inner_instance = inner_scope.resolve(ScopedService)
        assert outer_instance is not inner_instance

    def test_singleton_shared_across_scopes(self, container):
        container.register_singleton(SingletonService)
        container.register_scoped(ScopedService)
        scope1 = container.create_scope()
        scope2 = container.create_scope()
        s1_scope1 = scope1.resolve(SingletonService)
        s1_scope2 = scope2.resolve(SingletonService)
        s2_scope1 = scope1.resolve(ScopedService)
        s2_scope2 = scope2.resolve(ScopedService)
        assert s1_scope1 is s1_scope2
        assert s2_scope1 is not s2_scope2

    def test_with_statement_scope(self, container):
        container.register_scoped(ScopedService)
        with container.create_scope() as scope:
            instance = scope.resolve(ScopedService)
            assert isinstance(instance, ScopedService)


class TestEmptyContainer:
    def test_empty_container_resolve_raises_error(self, container):
        from solocoder_py.di import ServiceNotFoundError

        with __import__("pytest").raises(ServiceNotFoundError):
            container.resolve(SimpleService)


class TestScopeDisposal:
    def test_scoped_instance_unavailable_after_scope_dispose(self, container):
        import pytest

        container.register_scoped(ScopedService)
        scope = container.create_scope()
        scope.resolve(ScopedService)
        scope.dispose()
        with pytest.raises(ScopeDisposedError):
            scope.resolve(ScopedService)

    def test_disposed_scope_does_not_affect_other_scopes(self, container):
        container.register_scoped(ScopedService)
        scope1 = container.create_scope()
        scope2 = container.create_scope()
        scope1.resolve(ScopedService)
        scope1.dispose()
        instance2 = scope2.resolve(ScopedService)
        assert isinstance(instance2, ScopedService)


class TestDefaultLifetime:
    def test_default_lifetime_is_transient(self, container):
        container.register(SimpleService)
        instance1 = container.resolve(SimpleService)
        instance2 = container.resolve(SimpleService)
        assert instance1 is not instance2


class TestResolveFromRootContainer:
    def test_resolve_scoped_from_root_creates_implicit_scope(self, container):
        container.register_scoped(ScopedService)
        instance1 = container.resolve(ScopedService)
        instance2 = container.resolve(ScopedService)
        assert isinstance(instance1, ScopedService)
        assert isinstance(instance2, ScopedService)
