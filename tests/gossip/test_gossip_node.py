from __future__ import annotations

import threading

import pytest

from solocoder_py.gossip import (
    GossipConfig,
    GossipNode,
    HeartbeatMessage,
    ManualClock,
    Member,
    MemberState,
)

from .conftest import connect_nodes, make_config, make_node


class TestNodeBasicOperations:
    def test_node_creation_has_self(self, clock):
        node = make_node("n1", clock)
        assert node.node_id == "n1"
        assert node.membership.member_count() == 1
        self_member = node.membership.get_member("n1")
        assert self_member.state == MemberState.ALIVE

    def test_connect_nodes(self, clock):
        n1 = make_node("n1", clock)
        n2 = make_node("n2", clock)
        n1.connect(n2)
        assert "n2" in n1.get_connected_peers()
        assert "n1" in n2.get_connected_peers()

    def test_disconnect_nodes(self, clock):
        n1 = make_node("n1", clock)
        n2 = make_node("n2", clock)
        n1.connect(n2)
        n1.disconnect(n2)
        assert "n2" not in n1.get_connected_peers()
        assert "n1" not in n2.get_connected_peers()

    def test_seed_member(self, clock):
        node = make_node("n1", clock)
        node.seed_member("n2")
        m = node.membership.get_member("n2")
        assert m is not None
        assert m.state == MemberState.ALIVE


class TestHeartbeatPropagation:
    def test_single_heartbeat_updates_receiver(self, clock):
        cfg = make_config(fanout=1)
        n1 = make_node("n1", clock, config=cfg, seed=1)
        n2 = make_node("n2", clock, config=cfg, seed=2)
        n1.connect(n2)

        clock.advance(0.5)
        n1.seed_member("n2")
        n2.seed_member("n1")

        sent = n1.send_heartbeat()
        assert "n2" in sent

        n2_member = n2.membership.get_member("n1")
        assert n2_member is not None
        assert n2_member.state == MemberState.ALIVE

    def test_heartbeat_propagates_member_list(self, clock):
        cfg = make_config(fanout=1)
        n1 = make_node("n1", clock, config=cfg, seed=1)
        n2 = make_node("n2", clock, config=cfg, seed=2)
        n3 = make_node("n3", clock, config=cfg, seed=3)
        n1.connect(n2)
        n2.connect(n3)

        clock.advance(0.5)
        n1.seed_member("n2")
        n1.seed_member("n3")
        n2.seed_member("n1")

        n1.send_heartbeat()
        assert n2.membership.get_member("n3") is not None

    def test_heartbeat_respects_fanout(self, clock):
        cfg = make_config(fanout=2)
        n1 = make_node("n1", clock, config=cfg, seed=42)
        n2 = make_node("n2", clock, config=cfg)
        n3 = make_node("n3", clock, config=cfg)
        n4 = make_node("n4", clock, config=cfg)
        n5 = make_node("n5", clock, config=cfg)
        connect_nodes(n1, n2, n3, n4, n5)

        for n in [n2, n3, n4, n5]:
            n1.seed_member(n.node_id)
            n.seed_member("n1")

        sent = n1.send_heartbeat()
        assert len(sent) == 2

    def test_no_peers_no_heartbeat_sent(self, clock):
        node = make_node("n1", clock)
        sent = node.send_heartbeat()
        assert sent == []


class TestStateTransitions:
    def test_alive_to_suspect_to_dead(self, clock):
        cfg = make_config(suspect_missed_count=3, dead_timeout=5.0)
        n1 = make_node("n1", clock, config=cfg)
        n2 = make_node("n2", clock, config=cfg)
        n1.connect(n2)

        clock.advance(0.5)
        n1.seed_member("n2")

        for _ in range(2):
            transitions = n1.check_failures()
            assert "n2" not in transitions
        assert n1.membership.get_member("n2").state == MemberState.ALIVE

        transitions = n1.check_failures()
        assert transitions["n2"] == MemberState.SUSPECT

        clock.advance(4.9)
        transitions = n1.check_failures()
        assert "n2" not in transitions

        clock.advance(0.2)
        transitions = n1.check_failures()
        assert transitions["n2"] == MemberState.DEAD
        assert n1.membership.get_member("n2").state == MemberState.DEAD

    def test_heartbeat_recovery_from_suspect(self, clock):
        cfg = make_config(suspect_missed_count=3, dead_timeout=5.0, fanout=1)
        n1 = make_node("n1", clock, config=cfg, seed=1)
        n2 = make_node("n2", clock, config=cfg, seed=2)
        n1.connect(n2)

        clock.advance(0.5)
        n1.seed_member("n2")
        n2.seed_member("n1")

        for _ in range(3):
            n1.check_failures()
        assert n1.membership.get_member("n2").state == MemberState.SUSPECT

        clock.advance(0.1)
        n2.send_heartbeat()
        assert n1.membership.get_member("n2").state == MemberState.ALIVE

    def test_higher_version_alive_overrides_dead(self, clock):
        cfg = make_config(suspect_missed_count=3, dead_timeout=5.0, fanout=1)
        n1 = make_node("n1", clock, config=cfg, seed=1)
        n2 = make_node("n2", clock, config=cfg, seed=2)
        n1.connect(n2)

        clock.advance(0.5)
        n1.seed_member("n2")
        n2.seed_member("n1")

        for _ in range(3):
            n1.check_failures()
        clock.advance(5.1)
        n1.check_failures()
        assert n1.membership.get_member("n2").state == MemberState.DEAD

        n2.membership.rejoin_node("n2")
        clock.advance(0.1)
        n2.send_heartbeat()

        n2_member = n1.membership.get_member("n2")
        assert n2_member is not None
        assert n2_member.state == MemberState.ALIVE


class TestConcurrentViewMerging:
    def test_version_dominates_in_merge(self, clock):
        n1 = make_node("n1", clock)
        n2 = make_node("n2", clock)
        n3 = make_node("n3", clock)

        now = clock.now()
        old_member = Member("n4", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now)
        new_member = Member("n4", state=MemberState.SUSPECT, version=10, last_heartbeat=now, state_changed_at=now)

        msg_old = HeartbeatMessage(sender_id="n2", members={"n4": old_member})
        msg_new = HeartbeatMessage(sender_id="n3", members={"n4": new_member})

        n1.receive_heartbeat(msg_old)
        n1.receive_heartbeat(msg_new)

        stored = n1.membership.get_member("n4")
        assert stored.version == 10
        assert stored.state == MemberState.SUSPECT

    def test_old_version_does_not_override_new(self, clock):
        n1 = make_node("n1", clock)

        now = clock.now()
        new_member = Member("n4", state=MemberState.ALIVE, version=10, last_heartbeat=now, state_changed_at=now)
        old_member = Member("n4", state=MemberState.SUSPECT, version=1, last_heartbeat=now, state_changed_at=now)

        msg_new = HeartbeatMessage(sender_id="n2", members={"n4": new_member})
        msg_old = HeartbeatMessage(sender_id="n3", members={"n4": old_member})

        n1.receive_heartbeat(msg_new)
        n1.receive_heartbeat(msg_old)

        stored = n1.membership.get_member("n4")
        assert stored.version == 10
        assert stored.state == MemberState.ALIVE

    def test_concurrent_merges_converge(self, clock):
        nodes = [make_node(f"n{i}", clock) for i in range(5)]
        connect_nodes(*nodes)

        clock.advance(0.5)
        for i, node in enumerate(nodes):
            for j, other in enumerate(nodes):
                if i != j:
                    node.seed_member(other.node_id)

        for node in nodes:
            node.send_heartbeat()

        for node in nodes:
            node.send_heartbeat()

        for node in nodes:
            for other in nodes:
                m = node.membership.get_member(other.node_id)
                assert m is not None
                assert m.state == MemberState.ALIVE

    def test_incarnation_breaks_tie_for_rejoined_node(self, clock):
        n1 = make_node("n1", clock)

        now = clock.now()
        dead_member = Member("n5", state=MemberState.DEAD, version=5, incarnation=0, last_heartbeat=now, state_changed_at=now)
        rejoined_member = Member("n5", state=MemberState.ALIVE, version=1, incarnation=1, last_heartbeat=now, state_changed_at=now)

        msg_dead = HeartbeatMessage(sender_id="n2", members={"n5": dead_member})
        msg_rejoined = HeartbeatMessage(sender_id="n3", members={"n5": rejoined_member})

        n1.receive_heartbeat(msg_dead)
        n1.receive_heartbeat(msg_rejoined)

        stored = n1.membership.get_member("n5")
        assert stored.state == MemberState.ALIVE
        assert stored.incarnation == 1


class TestDeadNodeCleanup:
    def test_dead_nodes_cleaned_after_timeout(self, clock):
        cfg = make_config(suspect_missed_count=2, dead_timeout=1.0, cleanup_timeout=5.0)
        node = make_node("n1", clock, config=cfg)

        clock.advance(0.5)
        node.seed_member("n2")

        for _ in range(2):
            node.check_failures()
        clock.advance(1.1)
        node.check_failures()
        assert node.membership.get_member("n2").state == MemberState.DEAD

        clock.advance(4.9)
        removed = node.cleanup_dead_nodes()
        assert removed == []
        assert node.membership.get_member("n2") is not None

        clock.advance(0.2)
        removed = node.cleanup_dead_nodes()
        assert "n2" in removed
        assert node.membership.get_member("n2") is None

    def test_cleaned_node_rejoins_with_new_version(self, clock):
        cfg = make_config(suspect_missed_count=2, dead_timeout=1.0, cleanup_timeout=5.0, fanout=1)
        n1 = make_node("n1", clock, config=cfg, seed=1)
        n2 = make_node("n2", clock, config=cfg, seed=2)
        n1.connect(n2)

        clock.advance(0.5)
        n1.seed_member("n2")
        n2.seed_member("n1")

        for _ in range(2):
            n1.check_failures()
        clock.advance(1.1)
        n1.check_failures()
        clock.advance(5.1)
        removed = n1.cleanup_dead_nodes()
        assert "n2" in removed

        n2.membership.rejoin_node("n2")
        clock.advance(0.1)
        n2.send_heartbeat()

        stored = n1.membership.get_member("n2")
        assert stored is not None
        assert stored.state == MemberState.ALIVE
        assert stored.incarnation >= 1


class TestSingleNodeCluster:
    def test_single_node_cluster_stability(self, clock):
        cfg = make_config(suspect_missed_count=1, dead_timeout=2.0, cleanup_timeout=5.0)
        node = make_node("n1", clock, config=cfg)

        for _ in range(1000):
            transitions = node.check_failures()
        assert transitions == {}
        removed = node.cleanup_dead_nodes()
        assert removed == []
        assert node.membership.member_count() == 1
        assert node.membership.get_member("n1").state == MemberState.ALIVE

    def test_single_node_sends_no_heartbeat(self, clock):
        node = make_node("n1", clock)
        sent = node.send_heartbeat()
        assert sent == []


class TestAllNodesDead:
    def test_all_peers_marked_dead(self, clock):
        cfg = make_config(suspect_missed_count=2, dead_timeout=1.0)
        nodes = [make_node(f"n{i}", clock, config=cfg) for i in range(4)]
        connect_nodes(*nodes)

        clock.advance(0.5)
        for i, node in enumerate(nodes):
            for j, other in enumerate(nodes):
                if i != j:
                    node.seed_member(other.node_id)

        for _ in range(2):
            for node in nodes:
                node.check_failures()
        clock.advance(1.1)
        for node in nodes:
            node.check_failures()

        for node in nodes:
            for other in nodes:
                if other.node_id != node.node_id:
                    m = node.membership.get_member(other.node_id)
                    assert m is not None
                    assert m.state == MemberState.DEAD


class TestStateListener:
    def test_listener_notified_on_state_change(self, clock):
        cfg = make_config(suspect_missed_count=3, dead_timeout=5.0)
        node = make_node("n1", clock, config=cfg)

        changes = []

        def listener(node_id, old, new):
            changes.append((node_id, old, new))

        node.add_state_listener(listener)

        clock.advance(0.5)
        node.seed_member("n2")

        for _ in range(3):
            node.check_failures()

        assert ("n2", MemberState.ALIVE, MemberState.SUSPECT) in changes

        clock.advance(5.1)
        node.check_failures()
        assert ("n2", MemberState.SUSPECT, MemberState.DEAD) in changes

    def test_listener_notified_on_new_member_via_heartbeat(self, clock):
        cfg = make_config(fanout=1)
        n1 = make_node("n1", clock, config=cfg, seed=1)
        n2 = make_node("n2", clock, config=cfg, seed=2)
        n1.connect(n2)

        changes = []

        def listener(node_id, old, new):
            changes.append((node_id, old, new))

        n2.add_state_listener(listener)

        clock.advance(0.5)
        n1.seed_member("n2")

        n1.send_heartbeat()

        assert ("n1", None, MemberState.ALIVE) in changes or any(
            nid == "n1" and new == MemberState.ALIVE for (nid, _, new) in changes
        )


class TestMemberQueries:
    def test_query_online_suspect_dead(self, clock):
        cfg = make_config(suspect_missed_count=3, dead_timeout=5.0)
        node = make_node("n1", clock, config=cfg)

        clock.advance(0.5)
        node.seed_member("n2")
        node.seed_member("n3")
        node.seed_member("n4")

        node.check_failures()
        node.mark_node_alive("n3")
        node.check_failures()
        node.check_failures()

        clock.advance(5.1)
        node.check_failures()

        alive = node.membership.get_alive_members()
        suspect = node.membership.get_suspect_members()
        dead = node.membership.get_dead_members()

        assert "n1" in alive
        assert "n3" in alive or "n3" in suspect
        assert "n2" in dead or "n2" in suspect
        assert "n4" in dead or "n4" in suspect

    def test_last_heartbeat_and_version_tracked(self, clock):
        cfg = make_config(fanout=1)
        n1 = make_node("n1", clock, config=cfg, seed=1)
        n2 = make_node("n2", clock, config=cfg, seed=2)
        n1.connect(n2)

        clock.advance(1.0)
        n1.seed_member("n2")
        n2.seed_member("n1")

        t1 = clock.now()
        n1.send_heartbeat()
        m = n2.membership.get_member("n1")
        assert m.last_heartbeat >= t1
        assert m.version >= 1

        clock.advance(2.0)
        t2 = clock.now()
        n1.send_heartbeat()
        m2 = n2.membership.get_member("n1")
        assert m2.last_heartbeat >= t2
        assert m2.version > m.version


class TestMarkNodeAlive:
    def test_mark_dead_node_alive(self, clock):
        cfg = make_config(suspect_missed_count=2, dead_timeout=1.0)
        node = make_node("n1", clock, config=cfg)

        clock.advance(0.5)
        node.seed_member("n2")

        for _ in range(2):
            node.check_failures()
        clock.advance(1.1)
        node.check_failures()
        assert node.membership.get_member("n2").state == MemberState.DEAD

        node.mark_node_alive("n2")
        assert node.membership.get_member("n2").state == MemberState.ALIVE


class TestStartStop:
    def test_start_and_stop_dont_raise(self, clock):
        node = make_node("n1", clock)
        node.start()
        node.stop()
        node.start()
        node.stop()

    def test_start_idempotent(self, clock):
        node = make_node("n1", clock)
        node.start()
        node.start()
        node.stop()
