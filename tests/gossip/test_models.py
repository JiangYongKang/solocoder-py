from __future__ import annotations

import pytest

from solocoder_py.gossip import (
    GossipConfig,
    InvalidConfigError,
    ManualClock,
    Member,
    MemberState,
)

from .conftest import make_config


class TestMemberStateEnum:
    def test_states_exist(self):
        assert MemberState.ALIVE.value == "ALIVE"
        assert MemberState.SUSPECT.value == "SUSPECT"
        assert MemberState.DEAD.value == "DEAD"


class TestGossipConfigValidation:
    def test_default_config_valid(self):
        cfg = GossipConfig()
        assert cfg.heartbeat_interval == 1.0
        assert cfg.suspect_timeout == 5.0
        assert cfg.dead_timeout == 10.0
        assert cfg.cleanup_timeout == 60.0
        assert cfg.fanout == 3

    def test_rejects_non_positive_heartbeat_interval(self):
        with pytest.raises(InvalidConfigError):
            make_config(heartbeat_interval=0)
        with pytest.raises(InvalidConfigError):
            make_config(heartbeat_interval=-1)

    def test_rejects_non_positive_suspect_timeout(self):
        with pytest.raises(InvalidConfigError):
            make_config(suspect_timeout=0)

    def test_rejects_dead_timeout_not_greater_than_suspect(self):
        with pytest.raises(InvalidConfigError):
            make_config(suspect_timeout=5.0, dead_timeout=5.0)
        with pytest.raises(InvalidConfigError):
            make_config(suspect_timeout=5.0, dead_timeout=3.0)

    def test_rejects_cleanup_timeout_not_greater_than_dead(self):
        with pytest.raises(InvalidConfigError):
            make_config(dead_timeout=10.0, cleanup_timeout=10.0)
        with pytest.raises(InvalidConfigError):
            make_config(dead_timeout=10.0, cleanup_timeout=5.0)

    def test_rejects_non_positive_fanout(self):
        with pytest.raises(InvalidConfigError):
            make_config(fanout=0)


class TestMemberStateTransitions:
    def test_member_creation_defaults(self):
        clock = ManualClock()
        now = clock.now()
        m = Member(node_id="n1", last_heartbeat=now, state_changed_at=now)
        assert m.node_id == "n1"
        assert m.state == MemberState.ALIVE
        assert m.version == 0
        assert m.incarnation == 0
        assert m.missed_heartbeats == 0

    def test_mark_suspect_from_alive(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.ALIVE, version=1, last_heartbeat=clock.now(), state_changed_at=clock.now())
        clock.advance(1.0)
        before_version = m.version
        m.mark_suspect(clock.now())
        assert m.state == MemberState.SUSPECT
        assert m.version == before_version + 1
        assert m.missed_heartbeats == 0

    def test_mark_suspect_from_suspect_no_change(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.SUSPECT, version=3, last_heartbeat=clock.now(), state_changed_at=clock.now())
        m.mark_suspect(clock.now())
        assert m.state == MemberState.SUSPECT
        assert m.version == 3

    def test_mark_suspect_from_dead_no_change(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.DEAD, version=5, last_heartbeat=clock.now(), state_changed_at=clock.now())
        m.mark_suspect(clock.now())
        assert m.state == MemberState.DEAD
        assert m.version == 5

    def test_mark_dead_from_alive(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.ALIVE, version=1, last_heartbeat=clock.now(), state_changed_at=clock.now())
        before_version = m.version
        m.mark_dead(clock.now())
        assert m.state == MemberState.DEAD
        assert m.version == before_version + 1

    def test_mark_dead_from_suspect(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.SUSPECT, version=2, last_heartbeat=clock.now(), state_changed_at=clock.now())
        before_version = m.version
        m.mark_dead(clock.now())
        assert m.state == MemberState.DEAD
        assert m.version == before_version + 1

    def test_mark_dead_from_dead_no_change(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.DEAD, version=5, last_heartbeat=clock.now(), state_changed_at=clock.now())
        m.mark_dead(clock.now())
        assert m.state == MemberState.DEAD
        assert m.version == 5

    def test_mark_alive_from_dead_with_higher_version(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.DEAD, version=3, last_heartbeat=clock.now(), state_changed_at=clock.now())
        clock.advance(5.0)
        m.mark_alive(clock.now(), version=10)
        assert m.state == MemberState.ALIVE
        assert m.version == 10

    def test_mark_alive_increments_version(self):
        clock = ManualClock()
        m = Member(node_id="n1", state=MemberState.ALIVE, version=1, last_heartbeat=clock.now(), state_changed_at=clock.now())
        m.mark_alive(clock.now())
        assert m.state == MemberState.ALIVE
        assert m.version == 2

    def test_bump_version(self):
        clock = ManualClock(100.0)
        m = Member(node_id="n1", state=MemberState.ALIVE, version=5, last_heartbeat=50.0, state_changed_at=clock.now())
        m.bump_version(clock.now())
        assert m.version == 6
        assert m.last_heartbeat == 100.0


class TestMemberComparison:
    def test_incarnation_dominates(self):
        a = Member(node_id="n1", version=1, incarnation=2, last_heartbeat=100.0)
        b = Member(node_id="n1", version=100, incarnation=1, last_heartbeat=200.0)
        assert a.is_newer_than(b)
        assert not b.is_newer_than(a)

    def test_version_breaks_incarnation_tie(self):
        a = Member(node_id="n1", version=5, incarnation=1, last_heartbeat=100.0)
        b = Member(node_id="n1", version=3, incarnation=1, last_heartbeat=200.0)
        assert a.is_newer_than(b)
        assert not b.is_newer_than(a)

    def test_timestamp_breaks_version_incarnation_tie(self):
        a = Member(node_id="n1", version=5, incarnation=1, last_heartbeat=200.0)
        b = Member(node_id="n1", version=5, incarnation=1, last_heartbeat=100.0)
        assert a.is_newer_than(b)
        assert not b.is_newer_than(a)

    def test_equal_members_neither_newer(self):
        a = Member(node_id="n1", version=5, incarnation=1, last_heartbeat=100.0)
        b = Member(node_id="n1", version=5, incarnation=1, last_heartbeat=100.0)
        assert not a.is_newer_than(b)
        assert not b.is_newer_than(a)


class TestMemberClone:
    def test_clone_is_deep_copy(self):
        clock = ManualClock()
        m = Member(
            node_id="n1",
            state=MemberState.SUSPECT,
            incarnation=2,
            version=5,
            last_heartbeat=clock.now(),
            state_changed_at=clock.now(),
            missed_heartbeats=3,
        )
        c = m.clone()
        assert c.node_id == m.node_id
        assert c.state == m.state
        assert c.version == m.version
        c.state = MemberState.DEAD
        c.version = 999
        assert m.state == MemberState.SUSPECT
        assert m.version == 5
