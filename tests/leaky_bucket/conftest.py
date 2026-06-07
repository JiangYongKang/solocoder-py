from __future__ import annotations

import pytest

from solocoder_py.leaky_bucket import (
    BucketConfig,
    LeakyBucket,
    OverflowStrategy,
    SubjectLeakyBucketManager,
)
from solocoder_py.ratelimiter import ManualClock


@pytest.fixture
def manual_clock():
    return ManualClock(start_time=0.0)


@pytest.fixture
def bucket_config():
    return BucketConfig(capacity=5, leak_rate=2.0)


@pytest.fixture
def basic_bucket(manual_clock, bucket_config):
    return LeakyBucket(
        config=bucket_config,
        overflow_strategy=OverflowStrategy.REJECT_NEW,
        clock=manual_clock,
    )


@pytest.fixture
def default_manager(manual_clock):
    config = BucketConfig(capacity=3, leak_rate=1.0)
    return SubjectLeakyBucketManager(
        default_config=config,
        default_overflow_strategy=OverflowStrategy.REJECT_NEW,
        clock=manual_clock,
    )
