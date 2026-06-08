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


class TestOldLeaderStepDownOnNewElection:
    def test_new_election_steps_down_existing_leader(self, cluster_5):
        result1 = cluster_5.run_election("node-0")
        assert result1.is_successful is True
        assert cluster_5.leader_id == "node-0"
        old_leader = cluster_5.get_node("node-0")
        assert old_leader.state == NodeState.LEADER

        result2 = cluster_5.run_election("node-1")
        assert result2.is_successful is True
        assert cluster_5.leader_id == "node-1"
        assert old_leader.state != NodeState.LEADER
        new_leader = cluster_5.get_node("node-1")
        assert new_leader.state == NodeState.LEADER

        leader_count = sum(
            1 for n in cluster_5.list_nodes() if n.state == NodeState.LEADER
        )
        assert leader_count == 1

    def test_random_election_steps_down_existing_leader(self, cluster_5):
        cluster_5.run_election("node-0")
        old_leader = cluster_5.get_node("node-0")
        assert old_leader.state == NodeState.LEADER

        cluster_5.run_election_random()
        assert old_leader.state != NodeState.LEADER or cluster_5.leader_id != "node-0"

        leader_count = sum(
            1 for n in cluster_5.list_nodes() if n.state == NodeState.LEADER
        )
        assert leader_count <= 1


class TestVoteCountDeduplication:
    def test_duplicate_same_candidate_request_not_double_counted(self, cluster_5):
        from solocoder_py.leader_election import VoteRequest

        candidate = cluster_5.get_node("node-0")
        vote_request = candidate.start_election()
        voter = cluster_5.get_node("node-1")

        resp1 = voter.handle_vote_request(vote_request)
        assert resp1.vote_granted is True

        resp2 = voter.handle_vote_request(vote_request)
        assert resp2.vote_granted is False

    def test_cluster_election_no_duplicate_votes(self, cluster_5):
        result = cluster_5.run_election("node-0")
        votes = result.votes_received.get("node-0", [])
        assert len(votes) == cluster_5.node_count
        assert len(set(votes)) == len(votes)


class TestHeartbeatStaleTermStepsDown:
    def test_leader_steps_down_on_stale_term_heartbeat(self, cluster_5):
        cluster_5.run_election("node-0")
        assert cluster_5.leader_id == "node-0"
        old_leader = cluster_5.get_node("node-0")

        cluster_5.partition_node("node-0")
        cluster_5._leader_id = None

        cluster_5.run_election("node-1")
        assert cluster_5.leader_id == "node-1"
        assert cluster_5.current_term == 2

        cluster_5.heal_partition("node-0")

        new_leader = cluster_5.get_node("node-1")
        hb = new_leader.send_heartbeat()
        old_leader.receive_heartbeat(hb)
        assert old_leader.state == NodeState.FOLLOWER
        assert old_leader.current_term == 2
        assert old_leader.leader_id == "node-1"

    def test_cluster_heartbeat_detects_stale_term_and_steps_down(self, cluster_5):
        cluster_5.force_new_leader("node-1")
        assert cluster_5.current_term == 1

        stale_leader = cluster_5.get_node("node-0")
        stale_leader._state = NodeState.LEADER
        stale_leader._current_term = 1
        stale_leader._leader_id = "node-0"
        stale_leader._voted_for = "node-0"
        stale_leader._voted_term = 1

        for n in cluster_5.list_nodes():
            if n.node_id not in ("node-0", "node-1"):
                n._current_term = 2

        cluster_5._leader_id = "node-0"

        with pytest.raises(StaleTermError):
            cluster_5.leader_send_heartbeat()

        assert stale_leader.state == NodeState.FOLLOWER
        assert cluster_5.leader_id is None


class TestElectionTimeoutAutoTrigger:
    def test_no_auto_election_before_timeout(self, cluster_5_manual, manual_clock):
        result = cluster_5_manual.check_and_run_elections()
        assert result is None
        manual_clock.advance(1.0)
        result = cluster_5_manual.check_and_run_elections()
        assert result is None

    def test_auto_election_triggers_after_timeout(self, cluster_5_manual, manual_clock):
        manual_clock.advance(3.0)
        result = cluster_5_manual.check_and_run_elections()
        assert result is not None
        assert result.is_successful is True
        assert cluster_5_manual.leader_id is not None

    def test_heartbeat_prevents_auto_election(self, cluster_5_manual, manual_clock):
        cluster_5_manual.run_election("node-0")
        assert cluster_5_manual.leader_id == "node-0"

        for _ in range(10):
            manual_clock.advance(1.0)
            cluster_5_manual.leader_send_heartbeat()
            result = cluster_5_manual.check_and_run_elections()
            assert result is None

        assert cluster_5_manual.leader_id == "node-0"

    def test_partitioned_nodes_not_considered_for_timeout(self, cluster_5_manual, manual_clock):
        cluster_5_manual.partition_node("node-0")
        cluster_5_manual.partition_node("node-1")
        cluster_5_manual.partition_node("node-2")
        cluster_5_manual.partition_node("node-3")
        cluster_5_manual.partition_node("node-4")
        manual_clock.advance(10.0)
        result = cluster_5_manual.check_and_run_elections()
        assert result is None

    def test_auto_election_after_leader_partitioned(
        self, cluster_5_manual, manual_clock
    ):
        cluster_5_manual.run_election("node-0")
        cluster_5_manual.partition_node("node-0")
        cluster_5_manual._leader_id = None

        manual_clock.advance(3.0)
        result = cluster_5_manual.check_and_run_elections()
        assert result is not None
        assert result.is_successful is True
        assert cluster_5_manual.leader_id in {"node-1", "node-2", "node-3", "node-4"}


class TestClusterConfigurationValidation:
    def test_negative_election_timeout_rejected(self, make_cluster):
        with pytest.raises(ValueError):
            make_cluster(5, election_timeout_seconds=-1)

    def test_zero_election_timeout_rejected(self, make_cluster):
        with pytest.raises(ValueError):
            make_cluster(5, election_timeout_seconds=0)

    def test_negative_auto_election_interval_rejected(self):
        with pytest.raises(ValueError):
            LeaderElectionCluster(node_count=3, auto_election_interval=-1)

    def test_zero_auto_election_interval_rejected(self):
        with pytest.raises(ValueError):
            LeaderElectionCluster(node_count=3, auto_election_interval=0)


class TestBroadcastHeartbeatStaleTermInvalidatesElection:
    def test_run_election_broadcast_stale_term_returns_failed_result(self, cluster_5):
        from solocoder_py.leader_election import StaleTermError

        cluster_5.run_election("node-0")
        original_leader_id = cluster_5.leader_id
        assert original_leader_id == "node-0"

        cluster_5._leader_id = None
        cluster_5.get_node("node-0").step_down()

        def fake_broadcast(leader):
            raise StaleTermError("Simulated stale term during broadcast")

        original_broadcast = cluster_5._broadcast_heartbeat_from_leader
        try:
            cluster_5._broadcast_heartbeat_from_leader = fake_broadcast
            result = cluster_5.run_election("node-1")
            assert result.is_successful is False
            assert result.leader_id is None
            assert cluster_5.leader_id is None
            assert cluster_5.get_node("node-1").state == NodeState.FOLLOWER
        finally:
            cluster_5._broadcast_heartbeat_from_leader = original_broadcast

    def test_run_election_random_broadcast_stale_term_returns_failed_result(self, cluster_5):
        from solocoder_py.leader_election import StaleTermError

        cluster_5.run_election("node-0")
        cluster_5._leader_id = None
        cluster_5.get_node("node-0").step_down()

        def fake_broadcast(leader):
            raise StaleTermError("Simulated stale term during broadcast")

        original_broadcast = cluster_5._broadcast_heartbeat_from_leader
        try:
            cluster_5._broadcast_heartbeat_from_leader = fake_broadcast
            result = cluster_5.run_election_random()
            assert result.is_successful is False
            assert result.leader_id is None
            assert cluster_5.leader_id is None
            for node in cluster_5.list_nodes():
                if node.state == NodeState.LEADER:
                    assert False, f"Expected no LEADER nodes but found {node.node_id}"
        finally:
            cluster_5._broadcast_heartbeat_from_leader = original_broadcast

    def test_check_and_run_broadcast_stale_term_returns_failed_result(
        self, cluster_5_manual, manual_clock
    ):
        from solocoder_py.leader_election import StaleTermError

        cluster_5_manual.run_election("node-0")
        cluster_5_manual._leader_id = None
        cluster_5_manual.get_node("node-0").step_down()
        manual_clock.advance(10.0)

        def fake_broadcast(leader):
            raise StaleTermError("Simulated stale term during broadcast")

        original_broadcast = cluster_5_manual._broadcast_heartbeat_from_leader
        try:
            cluster_5_manual._broadcast_heartbeat_from_leader = fake_broadcast
            result = cluster_5_manual.check_and_run_elections()
            assert result is not None
            assert result.is_successful is False
            assert result.leader_id is None
            assert cluster_5_manual.leader_id is None
        finally:
            cluster_5_manual._broadcast_heartbeat_from_leader = original_broadcast


class TestLeaderHeartbeatErrorMessagePreservesId:
    def test_heartbeat_error_message_contains_original_leader_id(self, cluster_5):
        cluster_5.run_election("node-2")
        assert cluster_5.leader_id == "node-2"

        leader = cluster_5.get_node("node-2")
        leader._state = NodeState.FOLLOWER

        with pytest.raises(LeaderElectionError, match=r"Node node-2 is not leader"):
            cluster_5.leader_send_heartbeat()

    def test_heartbeat_no_leader_error_message(self, cluster_5):
        with pytest.raises(LeaderElectionError, match="No leader in cluster"):
            cluster_5.leader_send_heartbeat()


class TestAutoElectionBackgroundThread:
    def test_start_and_stop_auto_election(self):
        cluster = LeaderElectionCluster(
            node_count=3, election_timeout_seconds=0.1, auto_election_interval=0.05
        )
        assert cluster.is_auto_election_running is False

        cluster.start_auto_election()
        assert cluster.is_auto_election_running is True

        cluster.start_auto_election()
        assert cluster.is_auto_election_running is True

        cluster.stop_auto_election()
        assert cluster.is_auto_election_running is False

        cluster.stop_auto_election()
        assert cluster.is_auto_election_running is False

    def test_auto_election_thread_elects_leader_after_timeout(self):
        import time as real_time

        cluster = LeaderElectionCluster(
            node_count=3, election_timeout_seconds=0.1, auto_election_interval=0.02
        )
        try:
            cluster.start_auto_election()
            deadline = real_time.monotonic() + 2.0
            while real_time.monotonic() < deadline:
                if cluster.leader_id is not None:
                    break
                real_time.sleep(0.02)
            assert cluster.leader_id is not None
            leader = cluster.get_node(cluster.leader_id)
            assert leader.state == NodeState.LEADER
        finally:
            cluster.stop_auto_election()

    def test_auto_election_picks_new_leader_after_partition(self):
        import time as real_time

        cluster = LeaderElectionCluster(
            node_count=5, election_timeout_seconds=0.1, auto_election_interval=0.02
        )
        cluster.run_election("node-0")
        original_leader = cluster.leader_id
        assert original_leader == "node-0"

        cluster.partition_node("node-0")
        cluster._leader_id = None

        try:
            cluster.start_auto_election()
            deadline = real_time.monotonic() + 2.0
            while real_time.monotonic() < deadline:
                if cluster.leader_id is not None and cluster.leader_id != "node-0":
                    break
                real_time.sleep(0.02)
            assert cluster.leader_id is not None
            assert cluster.leader_id != "node-0"
        finally:
            cluster.stop_auto_election()

    def test_heartbeat_suppresses_auto_election(self):
        import time as real_time

        cluster = LeaderElectionCluster(
            node_count=3, election_timeout_seconds=0.3, auto_election_interval=0.02
        )
        cluster.run_election("node-0")
        original_leader = cluster.leader_id

        try:
            cluster.start_auto_election()
            for _ in range(10):
                cluster.leader_send_heartbeat()
                real_time.sleep(0.05)
            assert cluster.leader_id == original_leader
        finally:
            cluster.stop_auto_election()
