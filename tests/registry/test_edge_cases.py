from __future__ import annotations

from collections import Counter

import pytest

from solocoder_py.registry import (
    ServiceNotFoundError,
)
from solocoder_py.registry import ManualClock, ServiceRegistry

from .conftest import make_config, make_instance, make_registry


class TestWeightedSelection:
    def test_select_single_instance(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1", host="10.0.0.1", port=8080))
        selected = registry.select_instance("svc-1")
        assert selected.instance_id == "inst-1"
        assert selected.host == "10.0.0.1"
        assert selected.port == 8080

    def test_select_instance_distribution_with_weights(self):
        clock = ManualClock()
        config = make_config(default_ttl=1000.0)
        registry = make_registry(config=config, clock=clock, seed=42)

        registry.register(make_instance("inst-1", "svc-1", weight=1, port=8001))
        registry.register(make_instance("inst-2", "svc-1", weight=2, port=8002))
        registry.register(make_instance("inst-3", "svc-1", weight=7, port=8003))

        counts = Counter()
        total = 10000
        for _ in range(total):
            inst = registry.select_instance("svc-1")
            counts[inst.instance_id] += 1

        assert counts["inst-3"] > counts["inst-2"] > counts["inst-1"]
        assert 500 < counts["inst-1"] < 1500
        assert 1500 < counts["inst-2"] < 2500
        assert 6000 < counts["inst-3"] < 8000

    def test_select_instance_zero_weights_fallback_random(self):
        clock = ManualClock()
        registry = make_registry(clock=clock, seed=42)

        registry.register(make_instance("inst-1", "svc-1", weight=0, port=8001))
        registry.register(make_instance("inst-2", "svc-1", weight=0, port=8002))

        counts = Counter()
        for _ in range(1000):
            inst = registry.select_instance("svc-1")
            counts[inst.instance_id] += 1

        assert counts["inst-1"] > 0
        assert counts["inst-2"] > 0

    def test_select_instance_mixed_zero_and_positive_weights(self):
        clock = ManualClock()
        registry = make_registry(clock=clock, seed=123)

        registry.register(make_instance("inst-zero-1", "svc-1", weight=0, port=8001))
        registry.register(make_instance("inst-zero-2", "svc-1", weight=0, port=8002))
        registry.register(make_instance("inst-heavy", "svc-1", weight=10, port=8003))

        counts = Counter()
        for _ in range(5000):
            inst = registry.select_instance("svc-1")
            counts[inst.instance_id] += 1

        assert counts["inst-heavy"] == 5000
        assert counts["inst-zero-1"] == 0
        assert counts["inst-zero-2"] == 0

    def test_select_instance_single_zero_weight(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1", weight=0))
        selected = registry.select_instance("svc-1")
        assert selected.instance_id == "inst-1"

    def test_select_instance_equal_weights(self):
        clock = ManualClock()
        registry = make_registry(clock=clock, seed=42)

        registry.register(make_instance("inst-1", "svc-1", weight=5, port=8001))
        registry.register(make_instance("inst-2", "svc-1", weight=5, port=8002))

        counts = Counter()
        for _ in range(10000):
            inst = registry.select_instance("svc-1")
            counts[inst.instance_id] += 1

        ratio = counts["inst-1"] / counts["inst-2"]
        assert 0.8 < ratio < 1.2

    def test_select_instance_skips_expired(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1", port=8001))
        registry.register(make_instance("inst-2", "svc-1", port=8002))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-2")

        clock.advance(20.0)

        for _ in range(100):
            selected = registry.select_instance("svc-1")
            assert selected.instance_id == "inst-2"

    def test_select_instance_nonexistent_service_raises(self, registry: ServiceRegistry):
        with pytest.raises(ServiceNotFoundError):
            registry.select_instance("svc-nonexistent")

    def test_select_instance_all_expired_raises(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        clock.advance(100.0)

        with pytest.raises(ServiceNotFoundError):
            registry.select_instance("svc-1")

    def test_select_instance_returns_clone(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1", metadata={"env": "dev"}))
        selected1 = registry.select_instance("svc-1")
        selected1.metadata["env"] = "prod"

        selected2 = registry.select_instance("svc-1")
        assert selected2.metadata["env"] == "dev"


class TestTtlExpiration:
    def test_cleanup_expired_removes_expired_instances(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))
        registry.register(make_instance("inst-3", "svc-2"))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-1")
        registry.renew("svc-2", "inst-3")

        clock.advance(20.0)

        removed = registry.cleanup_expired()
        assert "svc-1" in removed
        assert "inst-2" in removed["svc-1"]
        assert "inst-1" not in removed.get("svc-1", [])
        assert "svc-2" not in removed

        assert registry.instance_count("svc-1") == 1
        assert registry.instance_count("svc-2") == 1

    def test_cleanup_expired_removes_service_when_all_instances_expired(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))

        clock.advance(100.0)

        removed = registry.cleanup_expired()
        assert "svc-1" in removed
        assert set(removed["svc-1"]) == {"inst-1", "inst-2"}
        assert registry.service_count() == 0

    def test_cleanup_expired_when_nothing_expired(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-2"))

        clock.advance(10.0)

        removed = registry.cleanup_expired()
        assert removed == {}
        assert registry.service_count() == 2

    def test_cleanup_expired_empty_registry(self, registry: ServiceRegistry):
        removed = registry.cleanup_expired()
        assert removed == {}

    def test_custom_ttl_config(self, clock: ManualClock):
        config = make_config(default_ttl=5.0)
        registry = make_registry(config=config, clock=clock)

        registry.register(make_instance("inst-1", "svc-1"))
        clock.advance(4.9)
        removed = registry.cleanup_expired()
        assert removed == {}

        clock.advance(0.2)
        removed = registry.cleanup_expired()
        assert "svc-1" in removed
        assert "inst-1" in removed["svc-1"]

    def test_cleanup_expired_multiple_services(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))
        registry.register(make_instance("inst-3", "svc-2"))
        registry.register(make_instance("inst-4", "svc-3"))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-1")
        registry.renew("svc-3", "inst-4")

        clock.advance(20.0)

        removed = registry.cleanup_expired()
        assert "svc-1" in removed
        assert "inst-2" in removed["svc-1"]
        assert "inst-1" not in removed["svc-1"]
        assert "svc-2" in removed
        assert "inst-3" in removed["svc-2"]
        assert "svc-3" not in removed

        assert registry.service_count() == 2
        assert set(registry.list_services()) == {"svc-1", "svc-3"}


class TestEdgeCases:
    def test_deregister_then_reregister_same_instance(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1", port=8080))
        registry.deregister("svc-1", "inst-1")

        assert registry.service_count() == 0

        registry.register(make_instance("inst-1", "svc-1", port=9090))
        assert registry.instance_count("svc-1") == 1
        instances = registry.get_instances("svc-1")
        assert instances[0].port == 9090

    def test_register_instance_to_removed_service(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        clock.advance(100.0)
        registry.service_count()
        assert registry.service_count() == 0

        registry.register(make_instance("inst-2", "svc-1"))
        assert registry.service_count() == 1
        assert registry.instance_count("svc-1") == 1

    def test_concurrent_renew_prevents_expiry(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))

        for i in range(5):
            clock.advance(10.0)
            registry.renew("svc-1", "inst-1")

        instances = registry.get_instances("svc-1")
        assert len(instances) == 1

    def test_select_after_all_instances_deregistered(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))

        registry.deregister("svc-1", "inst-1")
        registry.deregister("svc-1", "inst-2")

        with pytest.raises(ServiceNotFoundError):
            registry.select_instance("svc-1")

    def test_auto_evict_after_partial_deregister(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))
        registry.register(make_instance("inst-3", "svc-1"))

        registry.deregister("svc-1", "inst-2")
        assert registry.instance_count("svc-1") == 2

        clock.advance(100.0)
        registry.service_count()

        assert registry.service_count() == 0

    def test_large_number_of_instances(self, registry: ServiceRegistry):
        for i in range(100):
            registry.register(make_instance(f"inst-{i}", "svc-1", port=8000 + i))

        assert registry.instance_count("svc-1") == 100
        instances = registry.get_instances("svc-1")
        assert len(instances) == 100

        selected = registry.select_instance("svc-1")
        assert selected is not None

    def test_metadata_independence_between_instances(self, registry: ServiceRegistry):
        registry.register(make_instance("inst-1", "svc-1", metadata={"tag": "a"}))
        registry.register(make_instance("inst-2", "svc-1", metadata={"tag": "b"}))

        instances = {i.instance_id: i for i in registry.get_all_instances("svc-1")}
        assert instances["inst-1"].metadata["tag"] == "a"
        assert instances["inst-2"].metadata["tag"] == "b"

    def test_select_after_all_expired_auto_evicts_service(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        clock.advance(100.0)

        with pytest.raises(ServiceNotFoundError):
            registry.select_instance("svc-1")

        assert registry.service_count() == 0


class TestAutoEviction:
    def test_get_instances_triggers_auto_evict(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))
        registry.register(make_instance("inst-3", "svc-2"))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-1")

        clock.advance(20.0)

        instances = registry.get_instances("svc-1")
        assert len(instances) == 1
        assert instances[0].instance_id == "inst-1"

        with pytest.raises(ServiceNotFoundError):
            registry.get_instances("svc-2")

    def test_select_instance_triggers_auto_evict(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1", weight=5, port=8001))
        registry.register(make_instance("inst-2", "svc-1", weight=5, port=8002))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-1")

        clock.advance(20.0)

        for _ in range(50):
            selected = registry.select_instance("svc-1")
            assert selected.instance_id == "inst-1"

        instances = registry.get_all_instances("svc-1")
        assert len(instances) == 1
        assert instances[0].instance_id == "inst-1"

    def test_renew_triggers_auto_evict_other_instances(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))

        clock.advance(20.0)
        registry.renew("svc-1", "inst-1")

        clock.advance(15.0)

        registry.renew("svc-1", "inst-1")
        instances = registry.get_all_instances("svc-1")
        assert len(instances) == 1
        assert instances[0].instance_id == "inst-1"

    def test_deregister_triggers_auto_evict(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-2"))

        clock.advance(100.0)

        with pytest.raises(ServiceNotFoundError):
            registry.deregister("svc-1", "inst-1")

        assert registry.service_count() == 0

    def test_list_services_triggers_auto_evict(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-2"))

        clock.advance(100.0)
        assert registry.list_services() == []

    def test_register_triggers_auto_evict_other_services(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        assert len(registry.list_services()) == 1

        clock.advance(100.0)

        registry.register(make_instance("inst-2", "svc-2"))
        services = registry.list_services()
        assert len(services) == 1
        assert "svc-1" not in services
        assert "svc-2" in services

    def test_instance_count_triggers_auto_evict(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))

        clock.advance(100.0)
        count = registry.instance_count()
        assert count == 0
        assert registry.service_count() == 0

    def test_service_count_triggers_auto_evict(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-2"))

        clock.advance(100.0)
        count = registry.service_count()
        assert count == 0

    def test_renew_of_expired_instance_raises(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        clock.advance(100.0)

        with pytest.raises(ServiceNotFoundError):
            registry.renew("svc-1", "inst-1")

    def test_get_all_instances_triggers_auto_evict(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-1")

        clock.advance(20.0)
        all_instances = registry.get_all_instances("svc-1")
        assert len(all_instances) == 1
        assert all_instances[0].instance_id == "inst-1"

    def test_cleanup_expired_returns_removed_instances(self, registry: ServiceRegistry, clock: ManualClock):
        registry.register(make_instance("inst-1", "svc-1"))
        registry.register(make_instance("inst-2", "svc-1"))
        registry.register(make_instance("inst-3", "svc-2"))

        clock.advance(15.0)
        registry.renew("svc-1", "inst-1")

        clock.advance(20.0)

        removed = registry.cleanup_expired()
        assert "svc-1" in removed
        assert "inst-2" in removed["svc-1"]
        assert "inst-1" not in removed["svc-1"]
        assert "svc-2" in removed
        assert "inst-3" in removed["svc-2"]
