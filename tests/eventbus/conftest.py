import pytest

from solocoder_py.eventbus import EventBus


@pytest.fixture
def bus() -> EventBus:
    return EventBus()
