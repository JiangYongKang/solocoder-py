import pytest

from solocoder_py.leader_election import (
    AlreadyVotedError,
    NodeState,
    RaftNode,
    StaleTermError,
    VoteRequest,
)


class TestRaftNodeCreation:
    def test_node_initial_state(self):
        node = RaftNode(node_id="node-0")
        assert node.node_id == "node-0"
        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 0
        assert node.voted_for is None
        assert node.voted_term == 0
        assert node.leader_id is None

    def test_vote_record_initial(self):
        node = RaftNode(node_id="node-0")
        rec = node.vote_record
        assert rec.term == 0
        assert rec.voted_for is None


class TestRaftNodeElectionStart:
    def test_start_election_becomes_candidate(self):
        node = RaftNode(node_id="node-0")
        request = node.start_election()
        assert node.state == NodeState.CANDIDATE
        assert node.current_term == 1
        assert node.voted_for == "node-0"
        assert node.voted_term == 1
        assert node.leader_id is None
        assert request.term == 1
        assert request.candidate_id == "node-0"

    def test_start_election_increments_term(self):
        node = RaftNode(node_id="node-0")
        node._current_term = 5
        request = node.start_election()
        assert node.current_term == 6
        assert request.term == 6


class TestRaftNodeVoteRequestHandling:
    def test_handle_vote_request_grants_vote(self):
        node = RaftNode(node_id="node-1")
        request = VoteRequest(term=1, candidate_id="node-0")
        response = node.handle_vote_request(request)
        assert response.vote_granted is True
        assert response.term == 1
        assert response.voter_id == "node-1"
        assert node.voted_for == "node-0"
        assert node.voted_term == 1
        assert node.current_term == 1

    def test_handle_vote_request_rejects_stale_term(self):
        node = RaftNode(node_id="node-1")
        node._current_term = 5
        request = VoteRequest(term=3, candidate_id="node-0")
        response = node.handle_vote_request(request)
        assert response.vote_granted is False
        assert response.term == 5
        assert node.voted_for is None

    def test_handle_vote_request_updates_term(self):
        node = RaftNode(node_id="node-1")
        node._current_term = 1
        request = VoteRequest(term=5, candidate_id="node-0")
        response = node.handle_vote_request(request)
        assert node.current_term == 5
        assert response.term == 5

    def test_handle_vote_request_already_voted_different_candidate(self):
        node = RaftNode(node_id="node-1")
        node._current_term = 1
        node._voted_for = "node-2"
        node._voted_term = 1
        request = VoteRequest(term=1, candidate_id="node-0")
        with pytest.raises(AlreadyVotedError):
            node.handle_vote_request(request)

    def test_handle_vote_request_already_voted_same_candidate(self):
        node = RaftNode(node_id="node-1")
        node._current_term = 1
        node._voted_for = "node-0"
        node._voted_term = 1
        request = VoteRequest(term=1, candidate_id="node-0")
        response = node.handle_vote_request(request)
        assert response.vote_granted is False
        assert node.voted_for == "node-0"


class TestRaftNodeBecomeLeader:
    def test_become_leader_from_candidate(self):
        node = RaftNode(node_id="node-0")
        node.start_election()
        node.become_leader()
        assert node.state == NodeState.LEADER
        assert node.leader_id == "node-0"

    def test_become_leader_from_follower_fails(self):
        node = RaftNode(node_id="node-0")
        with pytest.raises(StaleTermError):
            node.become_leader()


class TestRaftNodeHeartbeat:
    def test_send_heartbeat_as_leader(self):
        node = RaftNode(node_id="node-0")
        node.start_election()
        node.become_leader()
        hb = node.send_heartbeat()
        assert hb.term == node.current_term
        assert hb.leader_id == "node-0"

    def test_send_heartbeat_as_follower_fails(self):
        node = RaftNode(node_id="node-0")
        with pytest.raises(StaleTermError):
            node.send_heartbeat()

    def test_receive_heartbeat_updates_leader(self):
        node = RaftNode(node_id="node-1")
        from solocoder_py.leader_election import Heartbeat

        hb = Heartbeat(term=1, leader_id="node-0")
        node.receive_heartbeat(hb)
        assert node.leader_id == "node-0"
        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 1

    def test_receive_heartbeat_stale_term_rejected(self):
        node = RaftNode(node_id="node-1")
        node._current_term = 5
        from solocoder_py.leader_election import Heartbeat

        hb = Heartbeat(term=3, leader_id="node-0")
        with pytest.raises(StaleTermError):
            node.receive_heartbeat(hb)

    def test_receive_heartbeat_steps_down_candidate(self):
        node = RaftNode(node_id="node-1")
        node.start_election()
        assert node.state == NodeState.CANDIDATE
        from solocoder_py.leader_election import Heartbeat

        hb = Heartbeat(term=node.current_term + 1, leader_id="node-0")
        node.receive_heartbeat(hb)
        assert node.state == NodeState.FOLLOWER

    def test_receive_heartbeat_steps_down_leader(self):
        node = RaftNode(node_id="node-1")
        node.start_election()
        node.become_leader()
        assert node.state == NodeState.LEADER
        from solocoder_py.leader_election import Heartbeat

        hb = Heartbeat(term=node.current_term + 1, leader_id="node-0")
        node.receive_heartbeat(hb)
        assert node.state == NodeState.FOLLOWER


class TestRaftNodeStepDown:
    def test_step_down_from_leader(self):
        node = RaftNode(node_id="node-0")
        node.start_election()
        node.become_leader()
        node.step_down()
        assert node.state == NodeState.FOLLOWER
        assert node.leader_id is None


class TestRaftNodeElectionTimeout:
    def test_node_initial_not_timed_out(self):
        from solocoder_py.leader_election import ManualClock

        clock = ManualClock()
        node = RaftNode(node_id="node-0", clock=clock, election_timeout_seconds=2.0)
        assert node.is_election_timed_out() is False

    def test_node_times_out_after_interval(self):
        from solocoder_py.leader_election import ManualClock

        clock = ManualClock()
        node = RaftNode(node_id="node-0", clock=clock, election_timeout_seconds=2.0)
        clock.advance(1.0)
        assert node.is_election_timed_out() is False
        clock.advance(1.0)
        assert node.is_election_timed_out() is True
        clock.advance(5.0)
        assert node.is_election_timed_out() is True

    def test_leader_never_times_out(self):
        from solocoder_py.leader_election import ManualClock

        clock = ManualClock()
        node = RaftNode(node_id="node-0", clock=clock, election_timeout_seconds=2.0)
        node.start_election()
        node.become_leader()
        assert node.state == NodeState.LEADER
        clock.advance(100.0)
        assert node.is_election_timed_out() is False

    def test_receive_heartbeat_resets_timeout(self):
        from solocoder_py.leader_election import ManualClock, Heartbeat

        clock = ManualClock()
        node = RaftNode(node_id="node-0", clock=clock, election_timeout_seconds=2.0)
        clock.advance(1.5)
        assert node.is_election_timed_out() is False
        hb = Heartbeat(term=1, leader_id="node-1")
        node.receive_heartbeat(hb)
        clock.advance(1.0)
        assert node.is_election_timed_out() is False
        clock.advance(1.0)
        assert node.is_election_timed_out() is True

    def test_start_election_resets_timeout(self):
        from solocoder_py.leader_election import ManualClock

        clock = ManualClock()
        node = RaftNode(node_id="node-0", clock=clock, election_timeout_seconds=2.0)
        clock.advance(1.9)
        assert node.is_election_timed_out() is False
        node.start_election()
        clock.advance(1.9)
        assert node.is_election_timed_out() is False

    def test_become_leader_resets_timeout(self):
        from solocoder_py.leader_election import ManualClock

        clock = ManualClock()
        node = RaftNode(node_id="node-0", clock=clock, election_timeout_seconds=2.0)
        node.start_election()
        clock.advance(1.9)
        node.become_leader()
        assert node.state == NodeState.LEADER
        clock.advance(100.0)
        assert node.is_election_timed_out() is False

    def test_step_down_resets_timeout(self):
        from solocoder_py.leader_election import ManualClock

        clock = ManualClock()
        node = RaftNode(node_id="node-0", clock=clock, election_timeout_seconds=2.0)
        node.start_election()
        node.become_leader()
        clock.advance(1.0)
        node.step_down()
        assert node.state == NodeState.FOLLOWER
        clock.advance(1.0)
        assert node.is_election_timed_out() is False
        clock.advance(1.0)
        assert node.is_election_timed_out() is True
