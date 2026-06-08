import pytest

from solocoder_py.leader_election import (
    ClusterStatus,
    ElectionResult,
    Heartbeat,
    NodeState,
    NodeStatus,
    VoteRecord,
    VoteRequest,
    VoteResponse,
)


class TestVoteRequest:
    def test_vote_request_creation(self):
        req = VoteRequest(term=1, candidate_id="node-0")
        assert req.term == 1
        assert req.candidate_id == "node-0"


class TestVoteResponse:
    def test_vote_response_creation(self):
        resp = VoteResponse(term=1, vote_granted=True, voter_id="node-1")
        assert resp.term == 1
        assert resp.vote_granted is True
        assert resp.voter_id == "node-1"


class TestHeartbeat:
    def test_heartbeat_creation(self):
        hb = Heartbeat(term=1, leader_id="node-0")
        assert hb.term == 1
        assert hb.leader_id == "node-0"


class TestVoteRecord:
    def test_vote_record_creation(self):
        rec = VoteRecord(term=1, voted_for="node-0")
        assert rec.term == 1
        assert rec.voted_for == "node-0"

    def test_vote_record_none(self):
        rec = VoteRecord(term=0, voted_for=None)
        assert rec.term == 0
        assert rec.voted_for is None


class TestElectionResult:
    def test_election_result_successful(self):
        result = ElectionResult(
            term=1,
            leader_id="node-0",
            votes_received={"node-0": ["node-0", "node-1", "node-2"]},
        )
        assert result.is_successful is True
        assert result.leader_id == "node-0"
        assert result.term == 1

    def test_election_result_unsuccessful(self):
        result = ElectionResult(
            term=1,
            leader_id=None,
            votes_received={"node-0": ["node-0"]},
        )
        assert result.is_successful is False


class TestNodeStatus:
    def test_node_status_creation(self):
        status = NodeStatus(
            node_id="node-0",
            state=NodeState.FOLLOWER,
            current_term=1,
            voted_for=None,
        )
        assert status.node_id == "node-0"
        assert status.state == NodeState.FOLLOWER
        assert status.current_term == 1
        assert status.voted_for is None


class TestClusterStatus:
    def test_cluster_status_creation(self):
        nodes = [
            NodeStatus(
                node_id=f"node-{i}",
                state=NodeState.FOLLOWER,
                current_term=1,
                voted_for=None,
            )
            for i in range(3)
        ]
        status = ClusterStatus(
            current_term=1, leader_id=None, nodes=nodes, last_election=None
        )
        assert status.current_term == 1
        assert status.leader_id is None
        assert len(status.nodes) == 3
