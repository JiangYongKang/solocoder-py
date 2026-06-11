import pytest

from solocoder_py.priority_threadpool import (
    ManualClock,
    PriorityThreadPool,
    ThreadPoolConfig,
)


@pytest.fixture
def manual_clock():
    return ManualClock(start_time=0.0)


@pytest.fixture
def make_pool(manual_clock):
    def _make(
        max_concurrency: int = 2,
        aging_threshold: float = 10.0,
        aging_check_interval: float = 1.0,
        clock=None,
    ) -> PriorityThreadPool:
        config = ThreadPoolConfig(
            max_concurrency=max_concurrency,
            aging_threshold=aging_threshold,
            aging_check_interval=aging_check_interval,
        )
        return PriorityThreadPool(
            config=config,
            clock=clock or manual_clock,
        )
    return _make
