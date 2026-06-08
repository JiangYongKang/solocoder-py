import pytest

from solocoder_py.backpressure import BackpressureStrategy, BoundedQueue


@pytest.fixture
def queue_block() -> BoundedQueue:
    return BoundedQueue(capacity=5, strategy=BackpressureStrategy.BLOCK)


@pytest.fixture
def queue_drop() -> BoundedQueue:
    return BoundedQueue(capacity=5, strategy=BackpressureStrategy.DROP)


@pytest.fixture
def queue_reject() -> BoundedQueue:
    return BoundedQueue(capacity=5, strategy=BackpressureStrategy.REJECT)


@pytest.fixture
def queue_with_watermarks() -> BoundedQueue:
    return BoundedQueue(
        capacity=10,
        strategy=BackpressureStrategy.BLOCK,
        high_watermark_ratio=0.8,
        low_watermark_ratio=0.2,
    )
