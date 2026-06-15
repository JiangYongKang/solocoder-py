from __future__ import annotations

import pytest

from solocoder_py.rate_limiter import (
    RateLimiter,
    SyncStrategy,
    TokenBucket,
    TokenBucketConfig,
)
from solocoder_py.ratelimiter import ManualClock


@pytest.fixture
def manual_clock():
    return ManualClock(start_time=0.0)


@pytest.fixture
def basic_config():
    return TokenBucketConfig(refill_rate=2.0, capacity=10)


@pytest.fixture
def burst_config():
    return TokenBucketConfig(refill_rate=1.0, capacity=20, initial_tokens=20)


@pytest.fixture
def empty_bucket_config():
    return TokenBucketConfig(refill_rate=5.0, capacity=10, initial_tokens=0)


@pytest.fixture
def basic_bucket(manual_clock, basic_config):
    return TokenBucket(config=basic_config, clock=manual_clock)


@pytest.fixture
def burst_bucket(manual_clock, burst_config):
    return TokenBucket(config=burst_config, clock=manual_clock)


@pytest.fixture
def empty_bucket(manual_clock, empty_bucket_config):
    return TokenBucket(config=empty_bucket_config, clock=manual_clock)


@pytest.fixture
def basic_rate_limiter(manual_clock, basic_config):
    return RateLimiter(
        config=basic_config,
        sync_strategy=SyncStrategy.MIN,
        clock=manual_clock,
    )


@pytest.fixture
def server_sync_limiter(manual_clock, basic_config):
    return RateLimiter(
        config=basic_config,
        sync_strategy=SyncStrategy.SERVER,
        clock=manual_clock,
    )


@pytest.fixture
def local_sync_limiter(manual_clock, basic_config):
    return RateLimiter(
        config=basic_config,
        sync_strategy=SyncStrategy.LOCAL,
        clock=manual_clock,
    )
