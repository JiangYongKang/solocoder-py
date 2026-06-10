from __future__ import annotations

import threading
from datetime import datetime

import pytest

from solocoder_py.sessionization import (
    InvalidEventError,
    InvalidSubjectError,
    InvalidThresholdError,
    ManualClock,
    Session,
    SessionError,
    SessionEvent,
    SessionNotFoundError,
    SessionizationError,
    Sessionizer,
    make_session,
    merge_sessions,
)
from .conftest import make_sessionizer


class TestModels:
    def test_session_event_creation(self):
        event_time = datetime(2025, 1, 1, 12, 0, 0)
        event = SessionEvent(subject_id="user1", event_time=event_time)
        assert event.subject_id == "user1"
        assert event.event_time == event_time
        assert event.event_type == "default"
        assert event.payload is None

    def test_session_event_with_type_and_payload(self):
        event_time = datetime(2025, 1, 1, 12, 0, 0)
        event = SessionEvent(
            subject_id="user1",
            event_time=event_time,
            event_type="click",
            payload={"page": "home"},
        )
        assert event.event_type == "click"
        assert event.payload == {"page": "home"}

    def test_session_event_empty_subject_raises(self):
        with pytest.raises(InvalidSubjectError, match="subject_id cannot be empty"):
            SessionEvent(subject_id="", event_time=datetime.now())

    def test_session_event_none_time_raises(self):
        with pytest.raises(InvalidEventError):
            SessionEvent(subject_id="user1", event_time=None)

    def test_make_session(self):
        event_time = datetime(2025, 1, 1, 12, 0, 0)
        event = SessionEvent(subject_id="user1", event_time=event_time)
        session = make_session("user1", event)
        assert session.subject_id == "user1"
        assert session.start_time == event_time
        assert session.end_time == event_time
        assert session.event_count == 1
        assert session.is_active is True
        assert len(session.events) == 1
        assert session.session_id

    def test_make_session_empty_subject_raises(self):
        event = SessionEvent(subject_id="user1", event_time=datetime.now())
        with pytest.raises(InvalidSubjectError):
            make_session("", event)

    def test_make_session_none_event_raises(self):
        with pytest.raises(InvalidEventError):
            make_session("user1", None)

    def test_make_session_subject_mismatch_raises(self):
        event = SessionEvent(subject_id="user1", event_time=datetime.now())
        with pytest.raises(InvalidEventError):
            make_session("user2", event)

    def test_session_add_event(self):
        event_time = datetime(2025, 1, 1, 12, 0, 0)
        event = SessionEvent(subject_id="user1", event_time=event_time)
        session = make_session("user1", event)

        later_time = datetime(2025, 1, 1, 12, 1, 0)
        later_event = SessionEvent(subject_id="user1", event_time=later_time)
        session.add_event(later_event)

        assert session.event_count == 2
        assert session.end_time == later_time
        assert len(session.events) == 2

    def test_session_duration(self):
        start = datetime(2025, 1, 1, 12, 0, 0)
        end = datetime(2025, 1, 1, 12, 5, 0)
        session = Session(
            session_id="s1",
            subject_id="user1",
            start_time=start,
            end_time=end,
        )
        assert session.duration == 300.0

    def test_session_close(self):
        event = SessionEvent(subject_id="user1", event_time=datetime.now())
        session = make_session("user1", event)
        assert session.is_active is True
        session.close()
        assert session.is_active is False

    def test_session_copy(self):
        event = SessionEvent(subject_id="user1", event_time=datetime.now())
        session = make_session("user1", event)
        copied = session.copy()
        assert copied.session_id == session.session_id
        assert copied.subject_id == session.subject_id
        copied.event_count = 999
        assert session.event_count == 1

    def test_merge_sessions(self):
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 10, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        s1 = make_session("user1", e1)
        s2 = make_session("user1", e2)

        merged = merge_sessions(s1, s2)
        assert merged.subject_id == "user1"
        assert merged.start_time == t1
        assert merged.end_time == t2
        assert merged.event_count == 2

    def test_merge_sessions_different_subjects_raises(self):
        e1 = SessionEvent(subject_id="user1", event_time=datetime.now())
        e2 = SessionEvent(subject_id="user2", event_time=datetime.now())
        s1 = make_session("user1", e1)
        s2 = make_session("user2", e2)
        with pytest.raises(InvalidSubjectError):
            merge_sessions(s1, s2)

    def test_merge_overlapping_sessions(self):
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 5, 0)
        t3 = datetime(2025, 1, 1, 12, 3, 0)
        t4 = datetime(2025, 1, 1, 12, 10, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        e3 = SessionEvent(subject_id="user1", event_time=t3)
        e4 = SessionEvent(subject_id="user1", event_time=t4)

        s1 = make_session("user1", e1)
        s1.add_event(e2)
        s2 = make_session("user1", e3)
        s2.add_event(e4)

        merged = merge_sessions(s1, s2)
        assert merged.start_time == t1
        assert merged.end_time == t4
        assert merged.event_count == 4


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(SessionError, SessionizationError)
        assert issubclass(SessionNotFoundError, SessionizationError)
        assert issubclass(InvalidEventError, SessionizationError)
        assert issubclass(InvalidSubjectError, SessionizationError)
        assert issubclass(InvalidThresholdError, SessionizationError)


class TestSessionizerCreation:
    def test_default_creation(self):
        sz = make_sessionizer()
        assert sz.idle_threshold == 300.0
        assert sz.merge_threshold == 0.0
        assert sz.timeout == 1800.0

    def test_custom_thresholds(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=30.0, timeout=600.0)
        assert sz.idle_threshold == 60.0
        assert sz.merge_threshold == 30.0
        assert sz.timeout == 600.0

    def test_negative_idle_threshold_raises(self):
        with pytest.raises(InvalidThresholdError):
            Sessionizer(idle_threshold=-1)

    def test_zero_idle_threshold_raises(self):
        with pytest.raises(InvalidThresholdError):
            Sessionizer(idle_threshold=0)

    def test_negative_merge_threshold_raises(self):
        with pytest.raises(InvalidThresholdError):
            Sessionizer(merge_threshold=-1)

    def test_zero_merge_threshold_ok(self):
        sz = Sessionizer(merge_threshold=0)
        assert sz.merge_threshold == 0.0

    def test_negative_timeout_raises(self):
        with pytest.raises(InvalidThresholdError):
            Sessionizer(timeout=-1)

    def test_zero_timeout_raises(self):
        with pytest.raises(InvalidThresholdError):
            Sessionizer(timeout=0)


class TestSessionSplitting:
    def test_single_event_creates_session(self):
        sz = make_sessionizer()
        event_time = datetime(2025, 1, 1, 12, 0, 0)
        event = SessionEvent(subject_id="user1", event_time=event_time)
        session = sz.add_event(event)
        assert session.subject_id == "user1"
        assert session.event_count == 1
        assert session.is_active is True

    def test_events_within_idle_threshold_same_session(self):
        sz = make_sessionizer(idle_threshold=300.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 4, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        s1 = sz.add_event(e1)
        s2 = sz.add_event(e2)

        assert s1.session_id == s2.session_id
        assert s2.event_count == 2

    def test_events_exceed_idle_threshold_new_session(self):
        sz = make_sessionizer(idle_threshold=300.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 10, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        s1 = sz.add_event(e1)
        s2 = sz.add_event(e2)

        assert s1.session_id != s2.session_id
        closed = sz.get_closed_sessions("user1")
        assert len(closed) == 1
        assert closed[0].session_id == s1.session_id

    def test_idle_gap_exactly_equal_to_threshold_same_session(self):
        sz = make_sessionizer(idle_threshold=300.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 5, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        s1 = sz.add_event(e1)
        s2 = sz.add_event(e2)

        assert s1.session_id == s2.session_id

    def test_idle_gap_just_over_threshold_new_session(self):
        sz = make_sessionizer(idle_threshold=300.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 5, 1)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        s1 = sz.add_event(e1)
        s2 = sz.add_event(e2)

        assert s1.session_id != s2.session_id

    def test_multiple_sessions_for_single_subject(self):
        sz = make_sessionizer(idle_threshold=60.0)
        base = datetime(2025, 1, 1, 12, 0, 0)

        for i in range(5):
            t = base.replace(minute=i * 10)
            event = SessionEvent(subject_id="user1", event_time=t)
            sz.add_event(event)

        closed = sz.get_closed_sessions("user1")
        active = sz.get_active_session("user1")
        total = len(closed) + (1 if active else 0)
        assert total == 5


class TestSessionMerge:
    def test_merge_with_zero_threshold_no_overlap_no_merge(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=0.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 5, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        sz.add_event(e1)
        sz.add_event(e2)

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 2

    def test_merge_with_threshold_less_than_gap_no_merge(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=60.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 5, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        sz.add_event(e1)
        sz.add_event(e2)

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 2

    def test_merge_with_threshold_greater_than_gap_merges(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=300.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 4, 59)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        sz.add_event(e1)
        sz.add_event(e2)

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 1
        assert merged[0].event_count == 2

    def test_merge_exactly_equal_to_threshold_not_merges(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=240.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 1, 0)
        t3 = datetime(2025, 1, 1, 12, 5, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        e3 = SessionEvent(subject_id="user1", event_time=t3)

        sz.add_event(e1)
        sz.add_event(e2)
        sz.add_event(e3)

        all_sessions = sz.get_all_sessions("user1")
        assert len(all_sessions) == 2

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 2
        assert merged[0].event_count == 2
        assert merged[1].event_count == 1

    def test_merge_less_than_threshold_merges(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=240.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 1, 0)
        t3 = datetime(2025, 1, 1, 12, 4, 59)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        e3 = SessionEvent(subject_id="user1", event_time=t3)

        sz.add_event(e1)
        sz.add_event(e2)
        sz.add_event(e3)

        all_sessions = sz.get_all_sessions("user1")
        assert len(all_sessions) == 2

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 1
        assert merged[0].event_count == 3

    def test_merge_greater_than_threshold_not_merges(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=240.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 1, 0)
        t3 = datetime(2025, 1, 1, 12, 5, 1)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        e3 = SessionEvent(subject_id="user1", event_time=t3)

        sz.add_event(e1)
        sz.add_event(e2)
        sz.add_event(e3)

        all_sessions = sz.get_all_sessions("user1")
        assert len(all_sessions) == 2

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 2

    def test_triple_merge_chain(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=120.0)
        times = [
            datetime(2025, 1, 1, 12, 0, 0),
            datetime(2025, 1, 1, 12, 1, 0),
            datetime(2025, 1, 1, 12, 2, 30),
            datetime(2025, 1, 1, 12, 4, 0),
        ]
        for t in times:
            event = SessionEvent(subject_id="user1", event_time=t)
            sz.add_event(event)

        all_sessions = sz.get_all_sessions("user1")
        assert len(all_sessions) == 3

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 1
        assert merged[0].event_count == 4

    def test_merge_active_session_also_closes(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=120.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 1, 59)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        sz.add_event(e1)
        sz.add_event(e2)

        assert sz.get_active_session("user1") is not None
        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 1
        assert merged[0].is_active is False
        assert sz.get_active_session("user1") is None

    def test_merge_single_session_returns_same(self):
        sz = make_sessionizer()
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 1

    def test_merge_empty_subject_returns_empty(self):
        sz = make_sessionizer()
        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 0


class TestSessionTimeout:
    def test_active_session_not_yet_timed_out(self):
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
        sz = make_sessionizer(timeout=600.0, clock=clock)
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        clock.advance_seconds(599)
        active = sz.get_active_session("user1")
        assert active is not None
        assert active.is_active is True

    def test_active_session_times_out_exactly(self):
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
        sz = make_sessionizer(timeout=600.0, clock=clock)
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        clock.advance_seconds(600)
        active = sz.get_active_session("user1")
        assert active is None

        closed = sz.get_closed_sessions("user1")
        assert len(closed) == 1

    def test_active_session_times_out_after(self):
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
        sz = make_sessionizer(timeout=600.0, clock=clock)
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        clock.advance_seconds(1000)
        active = sz.get_active_session("user1")
        assert active is None

    def test_check_timeouts_returns_closed_sessions(self):
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
        sz = make_sessionizer(timeout=600.0, clock=clock)

        for i in range(3):
            event = SessionEvent(
                subject_id=f"user{i}",
                event_time=datetime(2025, 1, 1, 12, 0, 0),
            )
            sz.add_event(event)

        clock.advance_seconds(1000)
        closed = sz.check_timeouts()
        assert len(closed) == 3

    def test_check_timeouts_partial(self):
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
        sz = make_sessionizer(timeout=600.0, clock=clock)

        for i in range(3):
            event = SessionEvent(
                subject_id=f"user{i}",
                event_time=datetime(2025, 1, 1, 12, 0, 0),
            )
            sz.add_event(event)

        clock.advance_seconds(300)
        sz.add_event(
            SessionEvent(
                subject_id="user2",
                event_time=datetime(2025, 1, 1, 12, 5, 0),
            )
        )

        clock.advance_seconds(400)
        closed = sz.check_timeouts()
        assert len(closed) == 2

    def test_session_closed_callback(self):
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
        sz = make_sessionizer(timeout=600.0, clock=clock)

        closed_sessions = []

        def on_close(s: Session) -> None:
            closed_sessions.append(s)

        sz.add_session_closed_callback(on_close)

        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        clock.advance_seconds(1000)
        sz.check_timeouts()

        assert len(closed_sessions) == 1
        assert closed_sessions[0].subject_id == "user1"

    def test_callback_on_idle_split(self):
        sz = make_sessionizer(idle_threshold=60.0)
        closed_count = [0]

        def on_close(s: Session) -> None:
            closed_count[0] += 1

        sz.add_session_closed_callback(on_close)

        e1 = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        e2 = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 5, 0)
        )

        sz.add_event(e1)
        assert closed_count[0] == 0
        sz.add_event(e2)
        assert closed_count[0] == 1


class TestSubjectIsolation:
    def test_different_subjects_have_separate_sessions(self):
        sz = make_sessionizer()
        t = datetime(2025, 1, 1, 12, 0, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t)
        e2 = SessionEvent(subject_id="user2", event_time=t)

        s1 = sz.add_event(e1)
        s2 = sz.add_event(e2)

        assert s1.session_id != s2.session_id
        assert sz.get_active_session("user1").session_id == s1.session_id
        assert sz.get_active_session("user2").session_id == s2.session_id

    def test_one_subject_timeout_does_not_affect_another(self):
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
        sz = make_sessionizer(timeout=600.0, clock=clock)

        e1 = SessionEvent(subject_id="user1", event_time=clock.now())
        e2 = SessionEvent(subject_id="user2", event_time=clock.now())
        sz.add_event(e1)
        sz.add_event(e2)

        clock.advance_seconds(300)
        sz.add_event(SessionEvent(subject_id="user2", event_time=clock.now()))

        clock.advance_seconds(400)
        sz.check_timeouts()

        assert sz.get_active_session("user1") is None
        assert sz.get_active_session("user2") is not None

    def test_merge_does_not_affect_other_subjects(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=300.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 4, 59)

        for uid in ["user1", "user2"]:
            sz.add_event(SessionEvent(subject_id=uid, event_time=t1))
            sz.add_event(SessionEvent(subject_id=uid, event_time=t2))

        sz.merge_adjacent_sessions("user1")

        u1_closed = sz.get_closed_sessions("user1")
        u2_all = sz.get_all_sessions("user2")
        assert len(u1_closed) == 1
        assert len(u2_all) == 2

    def test_clear_subject(self):
        sz = make_sessionizer()
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        assert sz.get_active_session("user1") is not None
        sz.clear_subject("user1")
        assert sz.get_active_session("user1") is None
        assert len(sz.get_closed_sessions("user1")) == 0

    def test_clear_all(self):
        sz = make_sessionizer()
        for i in range(3):
            event = SessionEvent(
                subject_id=f"user{i}",
                event_time=datetime(2025, 1, 1, 12, 0, 0),
            )
            sz.add_event(event)

        sz.clear_all()
        for i in range(3):
            assert sz.get_active_session(f"user{i}") is None
            assert len(sz.get_closed_sessions(f"user{i}")) == 0


class TestOutOfOrderEvents:
    def test_earlier_event_after_later_within_session(self):
        sz = make_sessionizer(idle_threshold=600.0)
        t_later = datetime(2025, 1, 1, 12, 5, 0)
        t_earlier = datetime(2025, 1, 1, 12, 2, 0)

        e1 = SessionEvent(subject_id="user1", event_time=t_later)
        e2 = SessionEvent(subject_id="user1", event_time=t_earlier)

        s1 = sz.add_event(e1)
        s2 = sz.add_event(e2)

        assert s1.session_id == s2.session_id
        assert s2.start_time == t_earlier
        assert s2.end_time == t_later

    def test_out_of_order_event_triggers_new_session_if_past_idle(self):
        sz = make_sessionizer(idle_threshold=60.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 10, 0)
        t3 = datetime(2025, 1, 1, 12, 1, 0)

        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        e3 = SessionEvent(subject_id="user1", event_time=t3)

        sz.add_event(e1)
        sz.add_event(e2)

        all_before = sz.get_all_sessions("user1")
        num_sessions_before = len(all_before)

        s3 = sz.add_event(e3)

        all_after = sz.get_all_sessions("user1")
        num_sessions_after = len(all_after)

        assert num_sessions_after > num_sessions_before
        assert s3.start_time == t3
        assert s3.end_time == t3

    def test_out_of_order_very_old_event_creates_new_session(self):
        sz = make_sessionizer(idle_threshold=60.0, timeout=3600.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 14, 0, 0)
        t_old = datetime(2025, 1, 1, 10, 0, 0)

        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        e_old = SessionEvent(subject_id="user1", event_time=t_old)

        sz.add_event(e1)
        sz.add_event(e2)

        num_closed_before = len(sz.get_closed_sessions("user1"))

        s_old = sz.add_event(e_old)
        num_closed_after = len(sz.get_closed_sessions("user1"))

        assert num_closed_after > num_closed_before
        assert s_old.start_time == t_old


class TestEdgeCases:
    def test_single_event_standalone_session(self):
        sz = make_sessionizer()
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)
        sz.force_close_all("user1")
        sessions = sz.get_closed_sessions("user1")
        assert len(sessions) == 1
        assert sessions[0].event_count == 1
        assert sessions[0].duration == 0.0

    def test_empty_subject_raises(self):
        sz = make_sessionizer()
        with pytest.raises(InvalidSubjectError):
            sz.add_event(SessionEvent(subject_id="", event_time=datetime.now()))

    def test_none_event_raises(self):
        sz = make_sessionizer()
        with pytest.raises(InvalidEventError):
            sz.add_event(None)

    def test_get_active_session_empty_subject_raises(self):
        sz = make_sessionizer()
        with pytest.raises(InvalidSubjectError):
            sz.get_active_session("")

    def test_get_active_session_unknown_subject_returns_none(self):
        sz = make_sessionizer()
        assert sz.get_active_session("nonexistent") is None

    def test_get_closed_sessions_unknown_subject_empty(self):
        sz = make_sessionizer()
        assert sz.get_closed_sessions("nonexistent") == []

    def test_close_session_active(self):
        sz = make_sessionizer()
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        s = sz.add_event(event)

        closed = sz.close_session("user1", s.session_id)
        assert closed.session_id == s.session_id
        assert sz.get_active_session("user1") is None

    def test_close_session_already_closed(self):
        sz = make_sessionizer()
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 10, 0)
        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)

        s1 = sz.add_event(e1)
        sz.add_event(e2)

        closed = sz.close_session("user1", s1.session_id)
        assert closed.session_id == s1.session_id
        assert closed.is_active is False

    def test_close_session_not_found_raises(self):
        sz = make_sessionizer()
        with pytest.raises(SessionNotFoundError):
            sz.close_session("user1", "nonexistent")

    def test_force_close_all_empty(self):
        sz = make_sessionizer()
        result = sz.force_close_all("user1")
        assert result == []

    def test_force_close_all_with_active(self):
        sz = make_sessionizer()
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        result = sz.force_close_all("user1")
        assert len(result) == 1
        assert result[0].is_active is False
        assert sz.get_active_session("user1") is None

    def test_merge_with_zero_threshold_and_overlap(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=0.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 5, 0)
        t3 = datetime(2025, 1, 1, 12, 3, 0)
        t4 = datetime(2025, 1, 1, 12, 8, 0)

        e1 = SessionEvent(subject_id="user1", event_time=t1)
        e2 = SessionEvent(subject_id="user1", event_time=t2)
        e3 = SessionEvent(subject_id="user1", event_time=t3)
        e4 = SessionEvent(subject_id="user1", event_time=t4)

        sz.add_event(e1)
        sz.add_event(e2)

        s2 = sz.get_active_session("user1")
        s2_id = s2.session_id

        sz.add_event(e3)
        sz.add_event(e4)

        closed = sz.get_closed_sessions("user1")
        has_first = any(s.start_time == t1 for s in closed)
        assert has_first

        active = sz.get_active_session("user1")
        assert active is not None

    def test_triple_overlap_merge(self):
        sz = make_sessionizer(idle_threshold=60.0, merge_threshold=500.0)
        times = [
            datetime(2025, 1, 1, 12, 0, 0),
            datetime(2025, 1, 1, 12, 2, 0),
            datetime(2025, 1, 1, 12, 5, 0),
            datetime(2025, 1, 1, 12, 7, 0),
            datetime(2025, 1, 1, 12, 9, 0),
            datetime(2025, 1, 1, 12, 11, 0),
        ]
        for t in times:
            sz.add_event(SessionEvent(subject_id="user1", event_time=t))

        closed = sz.get_closed_sessions("user1")
        assert len(closed) >= 2

        merged = sz.merge_adjacent_sessions("user1")
        assert len(merged) == 1
        assert merged[0].event_count == 6

    def test_get_all_sessions_sorted(self):
        sz = make_sessionizer(idle_threshold=60.0)
        times = [
            datetime(2025, 1, 1, 12, 0, 0),
            datetime(2025, 1, 1, 12, 10, 0),
            datetime(2025, 1, 1, 12, 20, 0),
        ]
        for t in times:
            sz.add_event(SessionEvent(subject_id="user1", event_time=t))

        all_sessions = sz.get_all_sessions("user1")
        assert len(all_sessions) == 3
        for i in range(len(all_sessions) - 1):
            assert all_sessions[i].start_time < all_sessions[i + 1].start_time

    def test_session_event_time_before_session_start(self):
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        session = make_session("user1", event)
        earlier_event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 11, 0, 0)
        )
        session.add_event(earlier_event)
        assert session.start_time == datetime(2025, 1, 1, 11, 0, 0)
        assert session.event_count == 2


class TestConcurrency:
    def test_concurrent_events_single_subject_no_duplicate_sessions(self):
        sz = make_sessionizer(idle_threshold=10000.0)
        errors = []
        event_count = 100

        def worker(start_idx: int):
            base = datetime(2025, 1, 1, 12, 0, 0)
            for i in range(start_idx, start_idx + 10):
                try:
                    from datetime import timedelta

                    t = base + timedelta(seconds=i)
                    event = SessionEvent(subject_id="user1", event_time=t)
                    sz.add_event(event)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i * 10,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        all_sessions = sz.get_all_sessions("user1")
        total_events = sum(s.event_count for s in all_sessions)
        assert total_events == event_count

    def test_concurrent_events_multiple_subjects_isolated(self):
        sz = make_sessionizer()
        errors = []

        def worker(subject: str):
            base = datetime(2025, 1, 1, 12, 0, 0)
            for i in range(20):
                try:
                    from datetime import timedelta

                    t = base + timedelta(seconds=i)
                    event = SessionEvent(subject_id=subject, event_time=t)
                    sz.add_event(event)
                except Exception as e:
                    errors.append(e)

        subjects = [f"user{i}" for i in range(5)]
        threads = [threading.Thread(target=worker, args=(s,)) for s in subjects]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for s in subjects:
            sessions = sz.get_all_sessions(s)
            assert len(sessions) == 1
            assert sessions[0].event_count == 20

    def test_concurrent_add_and_get(self):
        sz = make_sessionizer(idle_threshold=1000.0)
        errors = []

        def adder():
            base = datetime(2025, 1, 1, 12, 0, 0)
            for i in range(50):
                try:
                    from datetime import timedelta

                    t = base + timedelta(seconds=i)
                    event = SessionEvent(subject_id="user1", event_time=t)
                    sz.add_event(event)
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(50):
                try:
                    sz.get_active_session("user1")
                    sz.get_closed_sessions("user1")
                    sz.get_all_sessions("user1")
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=adder),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_clear_and_add(self):
        sz = make_sessionizer()
        errors = []

        def adder():
            base = datetime(2025, 1, 1, 12, 0, 0)
            for i in range(30):
                try:
                    from datetime import timedelta

                    t = base + timedelta(seconds=i)
                    event = SessionEvent(subject_id="user1", event_time=t)
                    sz.add_event(event)
                except Exception as e:
                    errors.append(e)

        def clearer():
            for _ in range(10):
                try:
                    sz.clear_subject("user1")
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=adder),
            threading.Thread(target=clearer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestCheckTimeoutsConcurrency:
    def test_check_timeouts_with_concurrent_add_event_no_exception(self):
        sz = make_sessionizer(timeout=10.0)
        errors = []
        base_time = datetime(2025, 1, 1, 12, 0, 0)

        for i in range(5):
            event = SessionEvent(
                subject_id=f"user{i}",
                event_time=base_time,
            )
            sz.add_event(event)

        def add_events():
            for i in range(50):
                try:
                    subject_idx = i % 5
                    event = SessionEvent(
                        subject_id=f"user{subject_idx}",
                        event_time=base_time,
                    )
                    sz.add_event(event)
                except Exception as e:
                    errors.append(e)

        def check_timeouts_loop():
            for _ in range(50):
                try:
                    sz.check_timeouts()
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=add_events),
            threading.Thread(target=check_timeouts_loop),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_check_timeouts_with_concurrent_clear_all_no_exception(self):
        sz = make_sessionizer(timeout=10.0)
        errors = []
        base_time = datetime(2025, 1, 1, 12, 0, 0)

        for i in range(5):
            event = SessionEvent(
                subject_id=f"user{i}",
                event_time=base_time,
            )
            sz.add_event(event)

        def check_timeouts_loop():
            for _ in range(30):
                try:
                    sz.check_timeouts()
                except Exception as e:
                    errors.append(e)

        def clear_all_loop():
            for i in range(30):
                try:
                    sz.clear_all()
                    for j in range(3):
                        event = SessionEvent(
                            subject_id=f"user{j}",
                            event_time=base_time,
                        )
                        sz.add_event(event)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=check_timeouts_loop),
            threading.Thread(target=clear_all_loop),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_check_timeouts_with_concurrent_clear_subject_no_exception(self):
        sz = make_sessionizer(timeout=10.0)
        errors = []
        base_time = datetime(2025, 1, 1, 12, 0, 0)

        for i in range(5):
            event = SessionEvent(
                subject_id=f"user{i}",
                event_time=base_time,
            )
            sz.add_event(event)

        def check_timeouts_loop():
            for _ in range(30):
                try:
                    sz.check_timeouts()
                except Exception as e:
                    errors.append(e)

        def clear_subject_loop():
            for i in range(30):
                try:
                    subject_idx = i % 5
                    sz.clear_subject(f"user{subject_idx}")
                    event = SessionEvent(
                        subject_id=f"user{subject_idx}",
                        event_time=base_time,
                    )
                    sz.add_event(event)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=check_timeouts_loop),
            threading.Thread(target=clear_subject_loop),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestEncapsulation:
    def test_get_active_session_returns_copy(self):
        sz = make_sessionizer()
        event = SessionEvent(
            subject_id="user1", event_time=datetime(2025, 1, 1, 12, 0, 0)
        )
        sz.add_event(event)

        active = sz.get_active_session("user1")
        active.event_count = 999

        reloaded = sz.get_active_session("user1")
        assert reloaded.event_count == 1

    def test_get_closed_sessions_returns_copies(self):
        sz = make_sessionizer(idle_threshold=60.0)
        t1 = datetime(2025, 1, 1, 12, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 5, 0)
        sz.add_event(SessionEvent(subject_id="user1", event_time=t1))
        sz.add_event(SessionEvent(subject_id="user1", event_time=t2))

        closed = sz.get_closed_sessions("user1")
        closed[0].event_count = 999

        reloaded = sz.get_closed_sessions("user1")
        assert reloaded[0].event_count == 1
