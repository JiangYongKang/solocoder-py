import pytest

from solocoder_py.streamstats import StreamStats


@pytest.fixture
def empty_stats():
    return StreamStats()
