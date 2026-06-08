import pytest

from solocoder_py.leader_election import LeaderElectionCluster


@pytest.fixture
def make_cluster():
    def _make(node_count: int = 5) -> LeaderElectionCluster:
        return LeaderElectionCluster(node_count=node_count)

    return _make


@pytest.fixture
def cluster_3(make_cluster):
    return make_cluster(3)


@pytest.fixture
def cluster_5(make_cluster):
    return make_cluster(5)


@pytest.fixture
def cluster_4(make_cluster):
    return make_cluster(4)
