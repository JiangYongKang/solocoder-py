import pytest

from solocoder_py.leader_election import LeaderElectionCluster, ManualClock


@pytest.fixture
def make_cluster():
    def _make(node_count: int = 5, clock=None, election_timeout_seconds: float = 5.0) -> LeaderElectionCluster:
        kwargs = {"node_count": node_count, "election_timeout_seconds": election_timeout_seconds}
        if clock is not None:
            kwargs["clock"] = clock
        return LeaderElectionCluster(**kwargs)

    return _make


@pytest.fixture
def manual_clock():
    return ManualClock()


@pytest.fixture
def cluster_3(make_cluster):
    return make_cluster(3)


@pytest.fixture
def cluster_5(make_cluster):
    return make_cluster(5)


@pytest.fixture
def cluster_4(make_cluster):
    return make_cluster(4)


@pytest.fixture
def cluster_5_manual(manual_clock, make_cluster):
    return make_cluster(5, clock=manual_clock, election_timeout_seconds=2.0)
