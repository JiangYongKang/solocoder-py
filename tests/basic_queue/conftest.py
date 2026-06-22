import pytest

from solocoder_py.basic_queue import BasicQueue


@pytest.fixture
def queue() -> BasicQueue[int]:
    return BasicQueue[int]()
