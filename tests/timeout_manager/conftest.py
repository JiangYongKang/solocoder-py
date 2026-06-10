from __future__ import annotations

import pytest

from solocoder_py.timeout_manager import (
    ManualClock,
    TimeoutManager,
)


def make_manager(
    *,
    clock: ManualClock | None = None,
) -> TimeoutManager:
    clk = clock or ManualClock()
    return TimeoutManager(clock=clk)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def manager(clock: ManualClock) -> TimeoutManager:
    return make_manager(clock=clock)
