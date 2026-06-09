from __future__ import annotations

import pytest

from solocoder_py.registry import (
    InstanceAlreadyRegisteredError,
    InstanceNotFoundError,
    NoAvailableInstanceError,
    ServiceNotFoundError,
)
from solocoder_py.registry import ManualClock, ServiceRegistry

from .conftest import make_config, make_instance, make_registry


class TestRegistryInitialization:
    def test_empty_registry(self, registry: ServiceRegistry):
        assert registry.service_count() == 0
        assert registry.instance_count() == 0
        assert registry.list_services() == []

    def test_registry_with_defaults(self):
        registry = ServiceRegistry()
        assert registry.config.default_ttl == 30.0


class TestServiceRegistration:
    def test_register_single_instance(self, registry: ServiceRegistry, clock: ManualClock):
        inst = make_instance("inst-1", "svc-1")
        registered = registry.register(inst)

        assert registered.instance_id == "inst-1"
        assert registered.service_name == "svc-1"
        assert registered.registered_at == clock.now()
        assert registered.last_heartbeat == clock.now()

        assert registry.service_count() == 1
        assert registry.instance_count("svc-1") == 1
        assert registry.instance_count() == 1
        assert "svc-1" in registry.list_services()

    def test_register_multiple_instances_same_service(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1", port=8080))
        registry.register(make_instance("inst-2", "svc-1", port=8081))
        registry.register(make_instance("inst-3", "svc-1", port=8082))

        assert registry.instance_count("svc-1") == 3
        assert registry.service_count() == 1

    def test_register_multiple_services(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-2"))

        assert registry.service_count() == 2
        assert set(registry.list_services()) == {"svc-1", "svc-2"}

    def test_register_duplicate_instance_raises(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        with pytest.raises(InstanceAlreadyRegisteredError, match="inst-1"):
            registry.register(make_instance("inst-1", "svc-1", port=9999))

    def test_register_returns_clone(self, registry: ServiceRegistry):
        original = make_instance("inst-1", "svc-1", metadata={"env": "dev"})
        registered = registry.register(original)

        assert registered is not original
        registered.metadata["env"] = "prod"
        assert original.metadata["env"] == "dev"

    def test_register_preserves_metadata(self, registry: ServiceRegistry):
        metadata = {"region": "us-west-2", "version": "v2.0.0", "az": "a"}
        inst = make_instance("inst-1", "svc-1", metadata=metadata)
        registered = registry.register(inst)

        assert registered.metadata == metadata
        assert registered.metadata is not metadata


class TestServiceRenew:
    def test_renew_updates_last_heartbeat(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        before = registry.get_all_instances("svc-1")[0]

        clock.advance(10.0)
        renewed = registry.renew("svc-1", "inst-1")

        assert renewed.last_heartbeat == clock.now()
        assert renewed.last_heartbeat > before.last_heartbeat

    def test_renew_nonexistent_service_raises(self, registry: ServiceRegistry):
        with pytest.raises(ServiceNotFoundError, match="nonexistent-svc"):
            registry.renew("nonexistent-svc", "inst-1")

    def test_renew_nonexistent_instance_raises(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        with pytest.raises(InstanceNotFoundError, match="inst-999"):
            registry.renew("svc-1", "inst-999")

    def test_renew_returns_clone(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        renewed1 = registry.renew("svc-1", "inst-1")
        clock.advance(5.0)
        renewed2 = registry.renew("svc-1", "inst-1")
        assert renewed1 is not renewed2


class TestServiceDeregistration:
    def test_deregister_instance(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))
        assert registry.instance_count("svc-1") == 2

        result = registry.deregister("svc-1", "inst-1")
        assert result is True
        assert registry.instance_count("svc-1") == 1

        instances = registry.get_all_instances("svc-1")
        assert all(i.instance_id != "inst-1" for i in instances)

    def test_deregister_last_instance_removes_service(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        assert registry.service_count() == 1

        registry.deregister("svc-1", "inst-1")
        assert registry.service_count() == 0
        assert "svc-1" not in registry.list_services()

        with pytest.raises(ServiceNotFoundError):
            registry.instance_count("svc-1")

    def test_deregister_nonexistent_service_raises(self, registry: ServiceRegistry):
        with pytest.raises(ServiceNotFoundError):
            registry.deregister("svc-nonexistent", "inst-1")

    def test_deregister_nonexistent_instance_raises(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        with pytest.raises(InstanceNotFoundError, match="inst-999"):
            registry.deregister("svc-1", "inst-999")

    def test_deregister_last_instance_multiple_services(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-2"))
        registry.register(make_instance("inst-3", "svc-2"))

        assert registry.service_count() == 2

        registry.deregister("svc-1", "inst-1")
        assert registry.service_count() == 1
        assert "svc-1" not in registry.list_services()
        assert "svc-2" in registry.list_services()


class TestServiceQuery:
    def test_get_instances_returns_only_available(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-1")

        clock.advance(20.0)

        instances = registry.get_instances("svc-1")
        instance_ids = {i.instance_id for i in instances}
        assert "inst-1" in instance_ids
        assert "inst-2" not in instance_ids

    def test_get_all_instances_auto_evicts_expired(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))

        assert registry.instance_count("svc-1") == 2

        clock.advance(100.0)

        with pytest.raises(ServiceNotFoundError):
            registry.get_all_instances("svc-1")

        assert registry.service_count() == 0

    def test_get_instances_nonexistent_service_raises(self, registry: ServiceRegistry):
        with pytest.raises(ServiceNotFoundError):
            registry.get_instances("svc-nonexistent")

    def test_get_instances_returns_clones(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1", metadata={"env": "dev"}))
        instances = registry.get_instances("svc-1")
        instances[0].metadata["env"] = "prod"

        instances2 = registry.get_instances("svc-1")
        assert instances2[0].metadata["env"] == "dev"
