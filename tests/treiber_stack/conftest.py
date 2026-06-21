import pytest

from solocoder_py.treiber_stack import TreiberStack


@pytest.fixture
def stack() -> TreiberStack[int]:
    return TreiberStack[int]()
