from __future__ import annotations

import pytest

from solocoder_py.gossip import (
    HeartbeatMessage,
    ManualClock,
    Member,
    MemberState,
    MembershipView,
)

from .conftest import make_config


class TestMembershipViewInitialization:
    def test_self_member_added_on_init(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        assert view.self_node_id == "n1"
        assert view.member_count() == 1
        self_member = view.get_member("n1")
        assert self_member is not None
        assert self_member.state == MemberState.ALIVE
        assert self_member.version >= 1

    def test_get_nonexistent_member(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        assert view.get_member("nonexistent") is None


class TestMembershipViewQueries:
    def test_get_alive_members(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n3", state=MemberState.SUSPECT, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n4", state=MemberState.DEAD, version=1, last_heartbeat=now, state_changed_at=now))

        alive = view.get_alive_members()
        assert "n1" in alive
        assert "n2" in alive
        assert "n3" not in alive
        assert "n4" not in alive

    def test_get_suspect_members(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n3", state=MemberState.SUSPECT, version=1, last_heartbeat=now, state_changed_at=now))

        suspects = view.get_suspect_members()
        assert "n3" in suspects
        assert "n1" not in suspects
        assert "n2" not in suspects

    def test_get_dead_members(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.DEAD, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n3", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))

        dead = view.get_dead_members()
        assert "n2" in dead
        assert "n1" not in dead
        assert "n3" not in dead

    def test_get_other_alive_node_ids(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n3", state=MemberState.SUSPECT, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n4", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))

        others = view.get_other_alive_node_ids()
        assert "n1" not in others
        assert "n2" in others
        assert "n4" in others
        assert "n3" not in others


class TestMembershipViewUpdates:
    def test_add_new_member(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        m = Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now)
        changed = view.add_or_update_member(m)
        assert changed is True
        assert view.member_count() == 2
        stored = view.get_member("n2")
        assert stored.state == MemberState.ALIVE
        assert stored.version == 1

    def test_update_with_higher_version(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))

        clock.advance(1.0)
        now2 = clock.now()
        changed = view.add_or_update_member(Member("n2", state=MemberState.SUSPECT, version=3, last_heartbeat=now2, state_changed_at=now2))
        assert changed is True
        stored = view.get_member("n2")
        assert stored.state == MemberState.SUSPECT
        assert stored.version == 3

    def test_update_with_lower_version_ignored(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=5, last_heartbeat=now, state_changed_at=now))

        changed = view.add_or_update_member(Member("n2", state=MemberState.SUSPECT, version=2, last_heartbeat=now, state_changed_at=now))
        assert changed is False
        stored = view.get_member("n2")
        assert stored.state == MemberState.ALIVE
        assert stored.version == 5

    def test_update_self_with_higher_version_alive(self):
        clock = ManualClock(50.0)
        view = MembershipView("n1", make_config(), clock)
        orig = view.get_member("n1")
        orig_version = orig.version

        changed = view.add_or_update_member(
            Member("n1", state=MemberState.ALIVE, version=orig_version + 5, last_heartbeat=100.0, state_changed_at=100.0)
        )
        assert changed is True
        stored = view.get_member("n1")
        assert stored.version == orig_version + 5

    def test_update_self_with_lower_version_ignored(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        orig = view.get_member("n1")
        orig_version = orig.version

        changed = view.add_or_update_member(
            Member("n1", state=MemberState.ALIVE, version=orig_version - 1, last_heartbeat=clock.now(), state_changed_at=clock.now())
        )
        assert changed is False
        stored = view.get_member("n1")
        assert stored.version == orig_version

    def test_update_self_heartbeat(self):
        clock = ManualClock(10.0)
        view = MembershipView("n1", make_config(), clock)
        before = view.get_member("n1")
        before_version = before.version

        clock.advance(2.0)
        view.update_self_heartbeat()
        after = view.get_member("n1")
        assert after.version == before_version + 1
        assert after.last_heartbeat == 12.0


class TestMembershipViewMergeHeartbeat:
    def test_merge_heartbeat_updates_members(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()

        msg = HeartbeatMessage(
            sender_id="n2",
            members={
                "n2": Member("n2", state=MemberState.ALIVE, version=2, last_heartbeat=now, state_changed_at=now),
                "n3": Member("n3", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now),
            },
        )

        results = view.merge_heartbeat(msg)
        assert results["n2"] is True
        assert results["n3"] is True
        assert view.get_member("n2") is not None
        assert view.get_member("n3") is not None

    def test_merge_heartbeat_preserves_newer_locals(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=5, last_heartbeat=now, state_changed_at=now))

        msg = HeartbeatMessage(
            sender_id="n3",
            members={"n2": Member("n2", state=MemberState.SUSPECT, version=2, last_heartbeat=now, state_changed_at=now)},
        )
        results = view.merge_heartbeat(msg)
        assert results["n2"] is False
        stored = view.get_member("n2")
        assert stored.state == MemberState.ALIVE
        assert stored.version == 5


class TestMembershipViewFailureDetection:
    def test_alive_to_suspect_after_missed_heartbeats(self):
        clock = ManualClock()
        cfg = make_config(suspect_missed_count=3, dead_timeout=10.0)
        view = MembershipView("n1", cfg, clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))

        for _ in range(2):
            transitions = view.check_failures()
            assert "n2" not in transitions
            assert view.get_member("n2").state == MemberState.ALIVE
        assert view.get_member("n2").missed_heartbeats == 2

        transitions = view.check_failures()
        assert transitions["n2"] == MemberState.SUSPECT
        assert view.get_member("n2").state == MemberState.SUSPECT
        assert view.get_member("n2").missed_heartbeats == 0

    def test_suspect_to_dead_after_timeout(self):
        clock = ManualClock()
        cfg = make_config(suspect_missed_count=3, dead_timeout=5.0)
        view = MembershipView("n1", cfg, clock)
        now = clock.now()
        suspect_member = Member("n2", state=MemberState.SUSPECT, version=2, last_heartbeat=now, state_changed_at=now)
        view.add_or_update_member(suspect_member)

        clock.advance(4.9)
        transitions = view.check_failures()
        assert "n2" not in transitions
        assert view.get_member("n2").state == MemberState.SUSPECT

        clock.advance(0.2)
        transitions = view.check_failures()
        assert transitions["n2"] == MemberState.DEAD
        assert view.get_member("n2").state == MemberState.DEAD

    def test_self_never_marked_suspect(self):
        clock = ManualClock()
        cfg = make_config(suspect_missed_count=1, dead_timeout=2.0)
        view = MembershipView("n1", cfg, clock)

        for _ in range(100):
            transitions = view.check_failures()
        assert "n1" not in transitions
        assert view.get_member("n1").state == MemberState.ALIVE

    def test_heartbeat_received_resets_missed_count(self):
        clock = ManualClock()
        cfg = make_config(suspect_missed_count=3, dead_timeout=10.0)
        view = MembershipView("n1", cfg, clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))

        view.check_failures()
        view.check_failures()
        assert view.get_member("n2").missed_heartbeats == 2

        clock.advance(1.0)
        now2 = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=2, last_heartbeat=now2, state_changed_at=now2))
        assert view.get_member("n2").missed_heartbeats == 0

        view.check_failures()
        assert view.get_member("n2").missed_heartbeats == 1
        transitions = view.check_failures()
        assert "n2" not in transitions


class TestMembershipViewCleanup:
    def test_dead_nodes_cleaned_up_after_timeout(self):
        clock = ManualClock()
        cfg = make_config(suspect_missed_count=5, dead_timeout=10.0, cleanup_timeout=60.0)
        view = MembershipView("n1", cfg, clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.DEAD, version=3, last_heartbeat=now, state_changed_at=now))

        clock.advance(59.0)
        removed = view.cleanup_dead_nodes()
        assert removed == []
        assert view.get_member("n2") is not None

        clock.advance(2.0)
        removed = view.cleanup_dead_nodes()
        assert "n2" in removed
        assert view.get_member("n2") is None

    def test_self_never_cleaned_up(self):
        clock = ManualClock()
        cfg = make_config(suspect_missed_count=1, dead_timeout=2.0, cleanup_timeout=3.0)
        view = MembershipView("n1", cfg, clock)

        clock.advance(100.0)
        removed = view.cleanup_dead_nodes()
        assert removed == []
        assert view.get_member("n1") is not None

    def test_alive_and_suspect_not_cleaned(self):
        clock = ManualClock()
        cfg = make_config(suspect_missed_count=5, dead_timeout=10.0, cleanup_timeout=60.0)
        view = MembershipView("n1", cfg, clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n3", state=MemberState.SUSPECT, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n4", state=MemberState.DEAD, version=1, last_heartbeat=now, state_changed_at=now))

        clock.advance(100.0)
        removed = view.cleanup_dead_nodes()
        assert "n4" in removed
        assert "n2" not in removed
        assert "n3" not in removed


class TestMembershipViewRejoin:
    def test_rejoin_node_gets_new_incarnation(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.DEAD, version=5, incarnation=0, last_heartbeat=now, state_changed_at=now))

        view.rejoin_node("n2")
        rejoined = view.get_member("n2")
        assert rejoined.state == MemberState.ALIVE
        assert rejoined.incarnation == 1
        assert rejoined.version == 1

    def test_rejoin_new_node_starts_at_incarnation_zero(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)

        view.rejoin_node("n99")
        rejoined = view.get_member("n99")
        assert rejoined.state == MemberState.ALIVE
        assert rejoined.incarnation == 0
        assert rejoined.version == 1


class TestMembershipViewBuildHeartbeat:
    def test_build_heartbeat_contains_all_members(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))
        view.add_or_update_member(Member("n3", state=MemberState.SUSPECT, version=2, last_heartbeat=now, state_changed_at=now))

        msg = view.build_heartbeat_message()
        assert msg.sender_id == "n1"
        assert "n1" in msg.members
        assert "n2" in msg.members
        assert "n3" in msg.members

    def test_heartbeat_message_is_snapshot(self):
        clock = ManualClock()
        view = MembershipView("n1", make_config(), clock)
        now = clock.now()
        view.add_or_update_member(Member("n2", state=MemberState.ALIVE, version=1, last_heartbeat=now, state_changed_at=now))

        msg = view.build_heartbeat_message()
        msg.members["n2"].state = MemberState.DEAD

        stored = view.get_member("n2")
        assert stored.state == MemberState.ALIVE
