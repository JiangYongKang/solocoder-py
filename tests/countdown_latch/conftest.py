from __future__ import annotations

import pytest

from solocoder_py.countdown_latch import CountdownLatch, ManualClock


def make_latch(count: int, clock: ManualClock | None = None) -> CountdownLatch:
    if clock is not None:
        return CountdownLatch(count=count, clock=clock)
    return CountdownLatch(count=count)


@pytest.fixture
def latch_factory():
    return make_latch


@pytest.fixture
def manual_clock():
    return ManualClock()
