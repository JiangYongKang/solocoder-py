from __future__ import annotations

from solocoder_py.di import Container, Lifetime

from .conftest import (
    Controller,
    Database,
    EmailNotifier,
    INotifier,
    Logger,
    Repository,
    ScopedService,
    ServiceWithCounter,
    SingletonService,
    SimpleService,
    TransientService,
)


class TestSingletonLifetime:
    def test_singleton_returns_same_instance_multiple_requests(self, container):
        container.register_singleton(SimpleService)
        instance1 = container.resolve(SimpleService)
        instance2 = container.resolve(SimpleService)
        instance3 = container.resolve(SimpleService)
        assert instance1 is instance2
        assert instance2 is instance3

    def test_singleton_constructor_executed_once(self, container):
        ServiceWithCounter.call_count = 0
        container.register_singleton(ServiceWithCounter)
        container.resolve(ServiceWithCounter)
        container.resolve(ServiceWithCounter)
        container.resolve(ServiceWithCounter)
        assert ServiceWithCounter.call_count == 1

    def test_register_method_with_singleton_lifetime(self, container):
        container.register(SimpleService, lifetime=Lifetime.SINGLETON)
        instance1 = container.resolve(SimpleService)
        instance2 = container.resolve(SimpleService)
        assert instance1 is instance2


class TestTransientLifetime:
    def test_transient_returns_new_instance_each_request(self, container):
        container.register_transient(SimpleService)
        instance1 = container.resolve(SimpleService)
        instance2 = container.resolve(SimpleService)
        instance3 = container.resolve(SimpleService)
        assert instance1 is not instance2
        assert instance2 is not instance3
        assert instance1 is not instance3

    def test_register_method_with_transient_lifetime(self, container):
        container.register(SimpleService, lifetime=Lifetime.TRANSIENT)
        instance1 = container.resolve(SimpleService)
        instance2 = container.resolve(SimpleService)
        assert instance1 is not instance2


class TestScopedLifetime:
    def test_scoped_same_instance_within_same_scope(self, container):
        container.register_scoped(ScopedService)
        scope = container.create_scope()
        instance1 = scope.resolve(ScopedService)
        instance2 = scope.resolve(ScopedService)
        instance3 = scope.resolve(ScopedService)
        assert instance1 is instance2
        assert instance2 is instance3

    def test_scoped_different_instance_across_scopes(self, container):
        container.register_scoped(ScopedService)
        scope1 = container.create_scope()
        scope2 = container.create_scope()
        instance1 = scope1.resolve(ScopedService)
        instance2 = scope2.resolve(ScopedService)
        assert instance1 is not instance2

    def test_register_method_with_scoped_lifetime(self, container):
        container.register(SimpleService, lifetime=Lifetime.SCOPED)
        scope = container.create_scope()
        instance1 = scope.resolve(SimpleService)
        instance2 = scope.resolve(SimpleService)
        assert instance1 is instance2


class TestConstructorInjection:
    def test_single_dependency_injected(self, container):
        container.register(Database)
        container.register(Repository)
        repo = container.resolve(Repository)
        assert isinstance(repo, Repository)
        assert isinstance(repo.database, Database)

    def test_multiple_dependencies_injected(self, container):
        container.register(Database)
        container.register(Repository)
        container.register(Logger)
        container.register(Controller)
        controller = container.resolve(Controller)
        assert isinstance(controller, Controller)
        assert isinstance(controller.repository, Repository)
        assert isinstance(controller.repository.database, Database)
        assert isinstance(controller.logger, Logger)

    def test_nested_dependencies_resolved(self, container):
        container.register(Database)
        container.register(Repository)
        container.register(Logger)
        container.register(Controller)
        controller = container.resolve(Controller)
        assert controller.repository.database is not None


class TestInterfaceRegistration:
    def test_register_by_interface_resolves_implementation(self, container):
        container.register(INotifier, EmailNotifier)
        notifier = container.resolve(INotifier)
        assert isinstance(notifier, EmailNotifier)

    def test_interface_with_dependencies(self, container):
        class IService:
            pass

        class ServiceImpl(IService):
            def __init__(self, database: Database) -> None:
                self.database = database

        container.register(Database)
        container.register(IService, ServiceImpl)
        service = container.resolve(IService)
        assert isinstance(service, ServiceImpl)
        assert isinstance(service.database, Database)
