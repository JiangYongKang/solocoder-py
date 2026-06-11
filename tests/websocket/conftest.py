import pytest

from solocoder_py.websocket import ManualClock


@pytest.fixture
def clock():
    return ManualClock()
