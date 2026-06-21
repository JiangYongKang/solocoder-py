import pytest

from solocoder_py.cmd_queue import CommandQueue


@pytest.fixture
def cmd_queue() -> CommandQueue:
    return CommandQueue()
