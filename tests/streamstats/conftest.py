import pytest

from solocoder_py.streamstats import StreamStats


@pytest.fixture
def empty_stats():
    return StreamStats()


@pytest.fixture
def seq_1_to_10_stats():
    s = StreamStats()
    for i in range(1, 11):
        s.add(i)
    return s
