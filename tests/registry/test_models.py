from __future__ import annotations

import pytest

from solocoder_py.registry import (
    InvalidConfigError,
    ManualClock,
    ServiceInstance,
)

from .conftest import make_instance


class TestServiceInstance:
    def test_instance_creation_defaults(self):
        inst = make_instance("inst-1", "svc-1")
        assert inst.instance_id == "inst-1"
        assert inst.service_name == "svc-1"
        assert inst.host == "127.0.0.1"
        assert inst.port == 8080
        assert inst.weight == 1
        assert inst.metadata == {}
        assert inst.registered_at == 0.0
        assert inst.last_heartbeat == 0.0

    def test_instance_creation_with_custom_values(self):
        inst = ServiceInstance(
            instance_id="inst-2",
            service_name="svc-2",
            host="10.0.0.1",
            port=9090,
            weight=10,
            metadata={"region": "us-east-1", "version": "v1"},
        )
        assert inst.host == "10.0.0.1"
        assert inst.port == 9090
        assert inst.weight == 10
        assert inst.metadata == {"region": "us-east-1", "version": "v1"}

    def test_instance_address_property(self):
        inst = make_instance("inst-1", host="192.168.1.1", port=8888)
        assert inst.address == "192.168.1.1:8888"

    def test_instance_clone_is_deep_copy(self):
        original = make_instance(
            "inst-1",
            weight=5,
            metadata={"env": "prod"},
        )
        original.registered_at = 100.0
        original.last_heartbeat = 200.0

        cloned = original.clone()
        assert cloned is not original
        assert cloned.instance_id == original.instance_id
        assert cloned.service_name == original.service_name
        assert cloned.weight == original.weight
        assert cloned.metadata == original.metadata
        assert cloned.metadata is not original.metadata
        assert cloned.registered_at == original.registered_at
        assert cloned.last_heartbeat == original.last_heartbeat

        cloned.metadata["env"] = "staging"
        assert original.metadata["env"] == "prod"

    def test_instance_is_expired(self):
        inst = make_instance("inst-1")
        inst.last_heartbeat = 100.0
        ttl = 30.0

        assert not inst.is_expired(110.0, ttl)
        assert not inst.is_expired(129.9, ttl)
        assert inst.is_expired(130.0, ttl)
        assert inst.is_expired(150.0, ttl)

    def test_negative_weight_rejected(self):
        with pytest.raises(InvalidConfigError, match="weight must be non-negative"):
            make_instance("inst-1", weight=-1)

    def test_zero_weight_is_allowed(self):
        inst = make_instance("inst-1", weight=0)
        assert inst.weight == 0


class TestRegistryConfig:
    def test_default_config(self):
        from solocoder_py.registry import RegistryConfig
        cfg = RegistryConfig()
        assert cfg.default_ttl == 30.0

    def test_custom_config(self):
        from solocoder_py.registry import RegistryConfig
        cfg = RegistryConfig(default_ttl=60.0)
        assert cfg.default_ttl == 60.0

    def test_invalid_ttl_rejected(self):
        from solocoder_py.registry import RegistryConfig
        with pytest.raises(InvalidConfigError, match="default_ttl must be positive"):
            RegistryConfig(default_ttl=0)
        with pytest.raises(InvalidConfigError, match="default_ttl must be positive"):
            RegistryConfig(default_ttl=-5.0)



