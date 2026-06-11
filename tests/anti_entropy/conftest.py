import pytest

from solocoder_py.anti_entropy import AntiEntropyEngine, Replica


@pytest.fixture
def replica_a():
    replica = Replica(replica_id="replica_a")
    return replica


@pytest.fixture
def replica_b():
    replica = Replica(replica_id="replica_b")
    return replica


@pytest.fixture
def engine(replica_a, replica_b):
    return AntiEntropyEngine(replica_a=replica_a, replica_b=replica_b)
