from __future__ import annotations

import pytest

from solocoder_py.watchdog import (
    HeartbeatWatchdog,
    ManualClock,
    WatchdogConfig,
)


def make_config(
    *,
    default_lease_ttl: float = 10.0,
    default_debounce_count: int = 3,
) -> WatchdogConfig:
    return WatchdogConfig(
        default_lease_ttl=default_lease_ttl,
        default_debounce_count=default_debounce_count,
    )


def make_watchdog(
    *,
    config: WatchdogConfig | None = None,
    clock: ManualClock | None = None,
) -> HeartbeatWatchdog:
    cfg = config or make_config()
    clk = clock or ManualClock()
    return HeartbeatWatchdog(config=cfg, clock=clk)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def config() -> WatchdogConfig:
    return make_config()


@pytest.fixture
def watchdog(clock: ManualClock, config: WatchdogConfig) -> HeartbeatWatchdog:
    return HeartbeatWatchdog(config=config, clock=clock)
