import pytest

from solocoder_py.deque import Deque


@pytest.fixture
def deque() -> Deque:
    return Deque()
