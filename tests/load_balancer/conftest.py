from __future__ import annotations

import pytest

from solocoder_py.load_balancer import (
    LoadBalancer,
    LoadBalancerConfig,
    ManualClock,
    SelectionStrategy,
)


def make_config(
    *,
    default_strategy: SelectionStrategy = SelectionStrategy.ROUND_ROBIN,
    failure_threshold: int = 3,
    recovery_timeout_seconds: float = 30.0,
    half_open_max_probes: int = 1,
) -> LoadBalancerConfig:
    return LoadBalancerConfig(
        default_strategy=default_strategy,
        failure_threshold=failure_threshold,
        recovery_timeout_seconds=recovery_timeout_seconds,
        half_open_max_probes=half_open_max_probes,
    )


def make_lb(
    *,
    config: LoadBalancerConfig | None = None,
    clock: ManualClock | None = None,
) -> LoadBalancer:
    cfg = config or make_config()
    clk = clock or ManualClock()
    return LoadBalancer(config=cfg, clock=clk)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def config() -> LoadBalancerConfig:
    return make_config()


@pytest.fixture
def lb(clock: ManualClock, config: LoadBalancerConfig) -> LoadBalancer:
    return LoadBalancer(config=config, clock=clock)
