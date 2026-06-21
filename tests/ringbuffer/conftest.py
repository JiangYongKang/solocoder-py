import pytest

from solocoder_py.ringbuffer import RingBuffer, WriteMode


@pytest.fixture
def rb_no_overwrite() -> RingBuffer[int]:
    return RingBuffer[int](capacity=5, write_mode=WriteMode.NO_OVERWRITE)


@pytest.fixture
def rb_overwrite() -> RingBuffer[int]:
    return RingBuffer[int](capacity=5, write_mode=WriteMode.OVERWRITE)


@pytest.fixture
def rb_small() -> RingBuffer[int]:
    return RingBuffer[int](capacity=3, write_mode=WriteMode.NO_OVERWRITE)
