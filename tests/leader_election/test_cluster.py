import pytest

from solocoder_py.leader_election import (
    AlreadyVotedError,
    LeaderElectionCluster,
    LeaderElectionError,
    NodeState,
    NodeNotFoundError,
    StaleTermError,
)


class TestClusterCreation:
    def test_cluster_creation(self, cluster_5):
        assert cluster_5.node_count == 5
        assert cluster_5.majority_count == 3
        assert cluster_5.leader_id is None
        assert cluster_5.current_term == 0
        assert len(cluster_5.list_nodes()) == 5

    def test_cluster_majority_3_nodes(self, cluster_3):
        assert cluster_3.majority_count == 2

    def test_cluster_majority_4_nodes(self, cluster_4):
        assert cluster_4.majority_count == 3

    def test_cluster_minimum_size(self):
        cluster = LeaderElectionCluster(node_count=1)
        assert cluster.node_count == 1
        assert cluster.majority_count == 1

    def test_cluster_zero_nodes_rejected(self):
        with pytest.raises(ValueError):
            LeaderElectionCluster(node_count=0)


class TestClusterNodeAccess:
    def test_get_node(self, cluster_5):
        node = cluster_5.get_node("node-0")
        assert node.node_id == "node-0"

    def test_get_node_not_found(self, cluster_5):
        with pytest.raises(NodeNotFoundError):
            cluster_5.get_node("nonexistent")

    def test_list_nodes(self, cluster_5):
        nodes = cluster_5.list_nodes()
        assert len(nodes) == 5
        assert {n.node_id for n in nodes} == {f"node-{i}" for i in range(5)}


class TestNormalElectionFlow:
    def test_single_node_election(self):
        cluster = LeaderElectionCluster(node_count=1)
        result = cluster.run_election("node-0")
        assert result.is_successful is True
        assert result.leader_id == "node-0"
        assert result.term == 1
        assert cluster.leader_id == "node-0"
        assert cluster.current_term == 1
        leader = cluster.get_node("node-0")
        assert leader.state == NodeState.LEADER

    def test_three_node_election(self, cluster_3):
        result = cluster_3.run_election("node-0")
        assert result.is_successful is True
        assert result.leader_id == "node-0"
        votes = result.votes_received.get("node-0", [])
        assert len(votes) >= cluster_3.majority_count
        leader = cluster_3.get_node("node-0")
        assert leader.state == NodeState.LEADER
        assert leader.current_term == 1

    def test_five_node_election(self, cluster_5):
        result = cluster_5.run_election("node-2")
        assert result.is_successful is True
        assert result.leader_id == "node-2"
        assert cluster_5.leader_id == "node-2"
        votes = result.votes_received["node-2"]
        assert len(votes) == 5

    def test_election_increments_term(self, cluster_5):
        result1 = cluster_5.run_election("node-0")
        assert result1.term == 1
        cluster_5.get_node("node-0").step_down()
        cluster_5._leader_id = None
        result2 = cluster_5.run_election("node-1")
        assert result2.term == 2
        assert cluster_5.current_term == 2

    def test_leader_sends_heartbeat(self, cluster_5):
        cluster_5.run_election("node-0")
        heartbeats = cluster_5.leader_send_heartbeat()
        assert len(heartbeats) == 1
        hb = heartbeats[0]
        assert hb.leader_id == "node-0"
        for node in cluster_5.list_nodes():
            if node.node_id != "node-0":
                assert node.leader_id == "node-0"
                assert node.state == NodeState.FOLLOWER

    def test_no_leader_heartbeat_fails(self, cluster_5):
        with pytest.raises(LeaderElectionError):
            cluster_5.leader_send_heartbeat()


class TestMajorityEdgeCases:
    def test_exact_majority_3_nodes(self, cluster_3):
        cluster_3.partition_node("node-2")
        result = cluster_3.run_election("node-0")
        assert result.is_successful is True
        votes = result.votes_received.get("node-0", [])
        assert len(votes) == 2
        assert len(votes) == cluster_3.majority_count
        assert cluster_3.leader_id == "node-0"

    def test_exact_majority_5_nodes(self, cluster_5):
        cluster_5.partition_node("node-3")
        cluster_5.partition_node("node-4")
        result = cluster_5.run_election("node-0")
        assert result.is_successful is True
        votes = result.votes_received.get("node-0", [])
        assert len(votes) == 3
        assert len(votes) == cluster_5.majority_count

    def test_even_nodes_majority_4_nodes(self, cluster_4):
        assert cluster_4.majority_count == 3
        result = cluster_4.run_election("node-0")
        assert result.is_successful is True
        votes = result.votes_received.get("node-0", [])
        assert len(votes) == 4 >= 3

    def test_insufficient_votes_fails_election(self, cluster_5):
        cluster_5.partition_node("node-1")
        cluster_5.partition_node("node-2")
        cluster_5.partition_node("node-3")
        result = cluster_5.run_election("node-0")
        assert result.is_successful is False
        assert result.leader_id is None
        assert cluster_5.leader_id is None
        candidate = cluster_5.get_node("node-0")
        assert candidate.state == NodeState.FOLLOWER

    def test_minority_partition_cannot_elect_leader(self, cluster_5):
        cluster_5.partition_node("node-2")
        cluster_5.partition_node("node-3")
        cluster_5.partition_node("node-4")
        result = cluster_5.run_election("node-0")
        assert result.is_successful is False


class TestStaleTermRejection:
    def test_stale_vote_request_rejected(self, cluster_5):
        cluster_5.run_election("node-0")
        assert cluster_5.current_term == 1
        node1 = cluster_5.get_node("node-1")
        from solocoder_py.leader_election import VoteRequest

        req = VoteRequest(term=0, candidate_id="node-2")
        response = node1.handle_vote_request(req)
        assert response.vote_granted is False
        assert response.term == 1

    def test_stale_heartbeat_rejected(self, cluster_5):
        cluster_5.run_election("node-0")
        cluster_5._leader_id = None
        cluster_5.run_election("node-1")
        assert cluster_5.current_term == 2
        node2 = cluster_5.get_node("node-2")
        from solocoder_py.leader_election import Heartbeat

        stale_hb = Heartbeat(term=1, leader_id="node-0")
        with pytest.raises(StaleTermError):
            node2.receive_heartbeat(stale_hb)


class TestDuplicateVoteRejection:
    def test_same_term_duplicate_vote_rejected(self, cluster_5):
        node1 = cluster_5.get_node("node-1")
        from solocoder_py.leader_election import VoteRequest

        req1 = VoteRequest(term=1, candidate_id="node-0")
        node1.handle_vote_request(req1)
        assert node1.voted_for == "node-0"
        req2 = VoteRequest(term=1, candidate_id="node-2")
        with pytest.raises(AlreadyVotedError):
            node1.handle_vote_request(req2)
        assert node1.voted_for == "node-0"

    def test_new_term_can_vote_again(self, cluster_5):
        node1 = cluster_5.get_node("node-1")
        from solocoder_py.leader_election import VoteRequest

        req1 = VoteRequest(term=1, candidate_id="node-0")
        node1.handle_vote_request(req1)
        assert node1.voted_for == "node-0"
        req2 = VoteRequest(term=2, candidate_id="node-2")
        node1.handle_vote_request(req2)
        assert node1.voted_for == "node-2"
        assert node1.current_term == 2


class TestOldLeaderPartitionRecovery:
    def test_old_leader_heartbeat_rejected_after_new_election(self, cluster_5):
        cluster_5.run_election("node-0")
        assert cluster_5.leader_id == "node-0"
        assert cluster_5.current_term == 1

        old_leader = cluster_5.get_node("node-0")
        cluster_5.partition_node("node-0")
        cluster_5._leader_id = None

        cluster_5.run_election("node-1")
        assert cluster_5.leader_id == "node-1"
        assert cluster_5.current_term == 2

        cluster_5.heal_partition("node-0")

        from solocoder_py.leader_election import Heartbeat

        stale_hb = Heartbeat(term=1, leader_id="node-0")
        with pytest.raises(StaleTermError):
            cluster_5.get_node("node-2").receive_heartbeat(stale_hb)

        assert old_leader.state != NodeState.LEADER or old_leader.current_term < 2

    def test_old_leader_steps_down_when_seeing_newer_term(self, cluster_5):
        cluster_5.run_election("node-0")
        old_leader = cluster_5.get_node("node-0")
        cluster_5.partition_node("node-0")
        cluster_5._leader_id = None
        cluster_5.run_election("node-1")
        cluster_5.heal_partition("node-0")

        new_leader = cluster_5.get_node("node-1")
        new_hb = new_leader.send_heartbeat()
        old_leader.receive_heartbeat(new_hb)

        assert old_leader.state == NodeState.FOLLOWER
        assert old_leader.current_term == 2
        assert old_leader.leader_id == "node-1"


class TestSplitBrainProtection:
    def test_split_brain_only_one_leader(self, cluster_5):
        cluster_5.run_election("node-0")
        assert cluster_5.leader_id == "node-0"

        cluster_5.partition_node("node-0")
        cluster_5.partition_node("node-3")
        cluster_5.partition_node("node-4")
        cluster_5._leader_id = None

        minority_result = cluster_5.run_election("node-1")
        assert minority_result.is_successful is False

        cluster_5.heal_partition("node-3")
        cluster_5.heal_partition("node-4")
        cluster_5.run_election("node-1")
        assert cluster_5.leader_id == "node-1"

        cluster_5.heal_partition("node-0")
        cluster_5.leader_send_heartbeat()

        leader_count = sum(
            1 for n in cluster_5.list_nodes() if n.state == NodeState.LEADER
        )
        assert leader_count == 1

    def test_higher_term_wins_split_brain(self, cluster_5):
        cluster_5.force_new_leader("node-0")
        assert cluster_5.current_term == 1

        cluster_5.partition_node("node-0")
        cluster_5._leader_id = None

        cluster_5.force_new_leader("node-1")
        assert cluster_5.current_term == 2

        cluster_5.heal_partition("node-0")

        node0 = cluster_5.get_node("node-0")
        node1 = cluster_5.get_node("node-1")
        assert node1.state == NodeState.LEADER
        assert node1.current_term == 2
        assert node0.current_term <= 2

        new_hb = node1.send_heartbeat()
        node0.receive_heartbeat(new_hb)
        assert node0.state == NodeState.FOLLOWER
        assert node0.current_term == 2
        assert node0.leader_id == "node-1"


class TestElectionStatusQueries:
    def test_get_node_status(self, cluster_5):
        cluster_5.run_election("node-0")
        status = cluster_5.get_node_status("node-0")
        assert status.node_id == "node-0"
        assert status.state == NodeState.LEADER
        assert status.current_term == 1
        status1 = cluster_5.get_node_status("node-1")
        assert status1.state == NodeState.FOLLOWER

    def test_get_vote_records(self, cluster_5):
        cluster_5.run_election("node-0")
        records = cluster_5.get_vote_records()
        assert len(records) == 5
        for nid, rec in records.items():
            assert rec.term >= 0

    def test_get_cluster_status(self, cluster_5):
        cluster_5.run_election("node-0")
        status = cluster_5.get_status()
        assert status.current_term == 1
        assert status.leader_id == "node-0"
        assert len(status.nodes) == 5
        assert status.last_election is not None
        assert status.last_election.is_successful is True

    def test_get_cluster_status_no_election(self, cluster_5):
        status = cluster_5.get_status()
        assert status.current_term == 0
        assert status.leader_id is None
        assert status.last_election is None

    def test_last_election_result(self, cluster_5):
        result = cluster_5.run_election("node-0")
        assert cluster_5.last_election is result
        assert cluster_5.last_election.term == 1
        assert cluster_5.last_election.leader_id == "node-0"


class TestRandomElection:
    def test_random_election(self, cluster_5):
        result = cluster_5.run_election_random()
        assert result.is_successful is True
        assert result.leader_id is not None
        assert cluster_5.leader_id is not None

    def test_random_election_with_partition(self, cluster_5):
        cluster_5.partition_node("node-3")
        cluster_5.partition_node("node-4")
        result = cluster_5.run_election_random()
        assert result.is_successful is True
        assert result.leader_id in {"node-0", "node-1", "node-2"}
