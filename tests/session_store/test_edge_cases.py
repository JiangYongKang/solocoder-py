import pytest

from solocoder_py.session_store import (
    EvictionStrategy,
    SessionExpiredError,
    SessionForciblyLoggedOutError,
    SessionIdleTimeoutError,
    SessionLimitExceededError,
)

from .conftest import FakeClock, make_config, make_store


class TestTTLEqualsIdleTimeout:
    def test_ttl_equals_idle_timeout_both_expire_together(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=30.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        clock.advance(29.0)
        info = store.get_session(session.session_id)
        assert info.session_id == session.session_id
        assert info.expires_at == clock.now() + 30.0
        assert info.idle_expires_at == clock.now() + 30.0

    def test_ttl_equals_idle_timeout_exactly_at_boundary(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=30.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        clock.advance(30.0)
        with pytest.raises(SessionExpiredError):
            store.get_session(session.session_id)

    def test_ttl_equals_idle_timeout_refresh_works(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=30.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        for i in range(5):
            clock.advance(20.0)
            info = store.get_session(session.session_id)
            assert info.session_id == session.session_id


class TestMaxConcurrentSessionsEqualsOne:
    def test_max_one_evicts_previous(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError):
            store.get_session(s1.session_id)

        info2 = store.get_session(s2.session_id)
        assert info2.session_id == s2.session_id

    def test_max_one_rejects_new(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.REJECT,
        )
        store.create_session("user-1", config=config)

        with pytest.raises(SessionLimitExceededError):
            store.create_session("user-1", config=config)

    def test_max_one_delete_then_create(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.REJECT,
        )
        s1 = store.create_session("user-1", config=config)
        store.delete_session(s1.session_id)
        s2 = store.create_session("user-1", config=config)
        assert s2.session_id != s1.session_id


class TestSameUserManySessions:
    def test_many_sessions_evicts_in_order(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=3,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        sessions = []
        for i in range(10):
            s = store.create_session("user-1", config=config)
            sessions.append(s)

        for i in range(7):
            with pytest.raises(SessionForciblyLoggedOutError):
                store.get_session(sessions[i].session_id)

        for i in range(7, 10):
            info = store.get_session(sessions[i].session_id)
            assert info.session_id == sessions[i].session_id

    def test_many_sessions_reject_after_limit(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=3,
            eviction_strategy=EvictionStrategy.REJECT,
        )
        for i in range(3):
            store.create_session("user-1", config=config)

        for i in range(5):
            with pytest.raises(SessionLimitExceededError):
                store.create_session("user-1", config=config)

    def test_access_pattern_preserves_lru(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(
            max_concurrent_sessions=3,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
            ttl=3600.0,
            idle_timeout=1800.0,
        )
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-1", config=config)
        s3 = store.create_session("user-1", config=config)

        clock.advance(1.0)
        store.get_session(s1.session_id)
        clock.advance(1.0)
        store.get_session(s2.session_id)

        s4 = store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError):
            store.get_session(s3.session_id)

        for s in [s1, s2, s4]:
            info = store.get_session(s.session_id)
            assert info.session_id == s.session_id


class TestExpirationBoundary:
    def test_expires_exactly_at_ttl_boundary(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=60.0, idle_timeout=60.0)
        session = store.create_session("user-1", config=config)

        clock.set(session.expires_at)
        with pytest.raises(SessionExpiredError):
            store.get_session(session.session_id)

    def test_expires_one_microsecond_before_ttl(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=60.0, idle_timeout=60.0)
        session = store.create_session("user-1", config=config)

        clock.set(session.expires_at - 0.000001)
        info = store.get_session(session.session_id)
        assert info.session_id == session.session_id

    def test_idle_timeout_exactly_at_boundary(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        clock.set(session.idle_expires_at)
        with pytest.raises(SessionIdleTimeoutError):
            store.get_session(session.session_id)

    def test_idle_timeout_one_microsecond_before(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        clock.set(session.idle_expires_at - 0.000001)
        info = store.get_session(session.session_id)
        assert info.session_id == session.session_id

    def test_idle_timeout_triggers_before_ttl(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=10.0)
        session = store.create_session("user-1", config=config)

        clock.advance(15.0)
        with pytest.raises(SessionIdleTimeoutError):
            store.get_session(session.session_id)

    def test_ttl_triggers_despite_no_idle_timeout(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=60.0, idle_timeout=60.0)
        session = store.create_session("user-1", config=config)

        for _ in range(5):
            clock.advance(5.0)
            store.get_session(session.session_id)

        clock.advance(61.0)
        with pytest.raises(SessionExpiredError):
            store.get_session(session.session_id)


class TestDataEdgeCases:
    def test_empty_data_dict(self):
        store = make_store()
        session = store.create_session("user-1", {})
        info = store.get_session(session.session_id)
        assert info.data == {}

    def test_large_data_dict(self):
        store = make_store()
        large_data = {f"key{i}": f"value{i}" for i in range(1000)}
        session = store.create_session("user-1", large_data)
        info = store.get_session(session.session_id)
        assert info.data == large_data
        assert len(info.data) == 1000

    def test_nested_data_update(self):
        store = make_store()
        session = store.create_session("user-1", {"nested": {"a": 1}})
        updated = store.update_session(
            session.session_id, {"nested": {"b": 2}}
        )
        assert updated.data == {"nested": {"b": 2}}

    def test_update_with_existing_keys_overwrites(self):
        store = make_store()
        session = store.create_session("user-1", {"a": 1, "b": 2})
        updated = store.update_session(session.session_id, {"a": 100})
        assert updated.data == {"a": 100, "b": 2}


class TestListSessionsEdgeCases:
    def test_list_sessions_filters_expired(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(
            max_concurrent_sessions=10, ttl=60.0, idle_timeout=30.0
        )
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-1", config=config)

        clock.advance(1.0)
        store.get_session(s2.session_id)

        clock.advance(60.0)
        sessions = store.list_sessions_by_user("user-1")
        assert len(sessions) == 0

    def test_list_sessions_after_eviction(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=2,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        s1 = store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)

        sessions = store.list_sessions_by_user("user-1")
        assert len(sessions) == 2
        ids = {s.session_id for s in sessions}
        assert s1.session_id not in ids
