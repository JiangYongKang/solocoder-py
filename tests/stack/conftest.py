import pytest

from solocoder_py.stack import Stack


@pytest.fixture
def stack() -> Stack:
    return Stack()
