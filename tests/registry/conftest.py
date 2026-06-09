from __future__ import annotations

import random

import pytest

from solocoder_py.registry import (
    ManualClock,
    RegistryConfig,
    ServiceInstance,
    ServiceRegistry,
)


def make_config(*, default_ttl: float = 30.0) -> RegistryConfig:
    return RegistryConfig(default_ttl=default_ttl)


def make_instance(
    instance_id: str,
    service_name: str = "test_service",
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    weight: int = 1,
    metadata: dict[str, str] | None = None,
) -> ServiceInstance:
    return ServiceInstance(
        instance_id=instance_id,
        service_name=service_name,
        host=host,
        port=port,
        weight=weight,
        metadata=metadata or {},
    )


def make_registry(
    *,
    config: RegistryConfig | None = None,
    clock: ManualClock | None = None,
    seed: int = 42,
) -> ServiceRegistry:
    cfg = config or make_config()
    clk = clock or ManualClock()
    rng = random.Random(seed)
    return ServiceRegistry(config=cfg, clock=clk, rng=rng)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def config() -> RegistryConfig:
    return make_config()


@pytest.fixture
def registry(clock: ManualClock, config: RegistryConfig) -> ServiceRegistry:
    return make_registry(config=config, clock=clock)
