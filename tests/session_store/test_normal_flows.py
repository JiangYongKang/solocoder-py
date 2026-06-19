import pytest

from solocoder_py.session_store import (
    EvictionStrategy,
    SessionForciblyLoggedOutError,
    generate_session_id,
)

from .conftest import FakeClock, make_config, make_store


class TestSessionIdGeneration:
    def test_generate_session_id_format(self):
        sid = generate_session_id()
        assert sid.startswith("sess_")
        assert len(sid) > len("sess_")

    def test_generate_session_id_uniqueness(self):
        ids = {generate_session_id() for _ in range(100)}
        assert len(ids) == 100


class TestSessionCreation:
    def test_create_session_basic(self):
        store = make_store()
        info = store.create_session("user-1", {"role": "admin"})
        assert info.session_id.startswith("sess_")
        assert info.user_id == "user-1"
        assert info.data == {"role": "admin"}
        assert info.ttl == 3600.0
        assert info.idle_timeout == 1800.0
        assert info.forcibly_logged_out is False
        assert info.forced_logout_reason is None
        assert info.created_at > 0
        assert info.expires_at == info.created_at + 3600.0
        assert info.idle_expires_at == info.created_at + 1800.0

    def test_create_session_without_data(self):
        store = make_store()
        info = store.create_session("user-1")
        assert info.data == {}

    def test_create_session_custom_config(self):
        store = make_store()
        config = make_config(ttl=7200.0, idle_timeout=3600.0)
        info = store.create_session("user-1", config=config)
        assert info.ttl == 7200.0
        assert info.idle_timeout == 3600.0
        assert info.expires_at == info.created_at + 7200.0
        assert info.idle_expires_at == info.created_at + 3600.0

    def test_create_multiple_sessions_unique_ids(self):
        store = make_store()
        sessions = [store.create_session(f"user-{i}") for i in range(10)]
        ids = [s.session_id for s in sessions]
        assert len(set(ids)) == 10

    def test_create_multiple_sessions_same_user(self):
        store = make_store()
        config = make_config(max_concurrent_sessions=10)
        sessions = [
            store.create_session("user-1", config=config) for _ in range(5)
        ]
        ids = [s.session_id for s in sessions]
        assert len(set(ids)) == 5
        for s in sessions:
            assert s.user_id == "user-1"


class TestSessionReadAndUpdate:
    def test_get_session_refreshes_sliding_expiration(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=60.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)
        original_expires_at = session.expires_at

        clock.advance(15.0)
        info = store.get_session(session.session_id)
        assert info.expires_at == clock.now() + 60.0
        assert info.expires_at > original_expires_at

    def test_get_session_refreshes_idle_timeout(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=60.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)
        original_idle_expires = session.idle_expires_at

        clock.advance(15.0)
        info = store.get_session(session.session_id)
        assert info.idle_expires_at == clock.now() + 30.0
        assert info.idle_expires_at > original_idle_expires

    def test_update_session_data_and_refresh(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=60.0, idle_timeout=30.0)
        session = store.create_session("user-1", {"a": 1}, config=config)
        original_expires_at = session.expires_at

        clock.advance(20.0)
        updated = store.update_session(session.session_id, {"b": 2, "a": 10})
        assert updated.data == {"a": 10, "b": 2}
        assert updated.expires_at == clock.now() + 60.0
        assert updated.expires_at > original_expires_at
        assert updated.idle_expires_at == clock.now() + 30.0

    def test_continuous_access_prevents_expiration(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=30.0, idle_timeout=15.0)
        session = store.create_session("user-1", config=config)

        for i in range(10):
            clock.advance(10.0)
            info = store.get_session(session.session_id)
            assert info.session_id == session.session_id

    def test_data_isolation_between_sessions(self):
        store = make_store()
        s1 = store.create_session("user-1", {"key": "value1"})
        s2 = store.create_session("user-1", {"key": "value2"})
        info1 = store.get_session(s1.session_id)
        info2 = store.get_session(s2.session_id)
        assert info1.data["key"] == "value1"
        assert info2.data["key"] == "value2"


class TestIdleTimeout:
    def test_idle_timeout_logout_within_ttl(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        from solocoder_py.session_store import SessionIdleTimeoutError

        clock.advance(31.0)
        with pytest.raises(SessionIdleTimeoutError, match="inactivity"):
            store.get_session(session.session_id)

    def test_access_before_idle_timeout_resets_timer(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        clock.advance(25.0)
        info = store.get_session(session.session_id)
        new_idle_deadline = info.idle_expires_at

        clock.advance(25.0)
        info2 = store.get_session(session.session_id)
        assert info2.idle_expires_at > new_idle_deadline

    def test_update_before_idle_timeout_resets_timer(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=30.0)
        session = store.create_session("user-1", config=config)

        clock.advance(25.0)
        store.update_session(session.session_id, {"k": "v"})

        clock.advance(25.0)
        info = store.get_session(session.session_id)
        assert info.session_id == session.session_id


class TestConcurrentSessionEviction:
    def test_evict_oldest_when_exceeding_limit(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=2,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-1", config=config)
        s3 = store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError, match="evicted"):
            store.get_session(s1.session_id)

        info2 = store.get_session(s2.session_id)
        assert info2.session_id == s2.session_id
        info3 = store.get_session(s3.session_id)
        assert info3.session_id == s3.session_id

    def test_evict_oldest_preserves_recently_accessed(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(
            max_concurrent_sessions=2,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
            ttl=3600.0,
            idle_timeout=1800.0,
        )
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-1", config=config)

        clock.advance(1.0)
        store.get_session(s1.session_id)

        s3 = store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError, match="evicted"):
            store.get_session(s2.session_id)

        info1 = store.get_session(s1.session_id)
        assert info1.session_id == s1.session_id
        info3 = store.get_session(s3.session_id)
        assert info3.session_id == s3.session_id

    def test_reject_strategy_prevents_new_session(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=2,
            eviction_strategy=EvictionStrategy.REJECT,
        )
        store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)

        from solocoder_py.session_store import SessionLimitExceededError

        with pytest.raises(SessionLimitExceededError, match="exceeded"):
            store.create_session("user-1", config=config)

    def test_evicted_session_returns_specific_error(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        s1 = store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError) as exc:
            store.get_session(s1.session_id)
        assert "evicted" in str(exc.value)
        assert "concurrent session limit" in str(exc.value)

    def test_eviction_is_per_user(self):
        store = make_store()
        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        u1_s1 = store.create_session("user-1", config=config)
        u2_s1 = store.create_session("user-2", config=config)

        store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError):
            store.get_session(u1_s1.session_id)

        info = store.get_session(u2_s1.session_id)
        assert info.session_id == u2_s1.session_id


class TestSessionDeletionAndListing:
    def test_delete_session(self):
        store = make_store()
        session = store.create_session("user-1")
        assert store.delete_session(session.session_id) is True

        from solocoder_py.session_store import SessionNotFoundError

        with pytest.raises(SessionNotFoundError):
            store.get_session(session.session_id)

    def test_delete_nonexistent_session_returns_false(self):
        store = make_store()
        assert store.delete_session("nonexistent") is False

    def test_list_sessions_by_user(self):
        store = make_store()
        config = make_config(max_concurrent_sessions=10)
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-1", config=config)
        store.create_session("user-2", config=config)

        sessions = store.list_sessions_by_user("user-1")
        assert len(sessions) == 2
        ids = {s.session_id for s in sessions}
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_list_sessions_empty_user(self):
        store = make_store()
        assert store.list_sessions_by_user("nobody") == []

    def test_logout_all_sessions(self):
        store = make_store()
        config = make_config(max_concurrent_sessions=10)
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-1", config=config)
        store.create_session("user-2", config=config)

        count = store.logout_all_sessions("user-1", reason="admin logout")
        assert count == 2

        with pytest.raises(SessionForciblyLoggedOutError) as exc:
            store.get_session(s1.session_id)
        assert "admin logout" in str(exc.value)

        with pytest.raises(SessionForciblyLoggedOutError):
            store.get_session(s2.session_id)

    def test_logout_all_sessions_empty_user(self):
        store = make_store()
        assert store.logout_all_sessions("nobody") == 0

    def test_clear_store(self):
        store = make_store()
        config = make_config(max_concurrent_sessions=10)
        s1 = store.create_session("user-1", config=config)
        s2 = store.create_session("user-2", config=config)
        store.clear()

        from solocoder_py.session_store import SessionNotFoundError

        with pytest.raises(SessionNotFoundError):
            store.get_session(s1.session_id)
        with pytest.raises(SessionNotFoundError):
            store.get_session(s2.session_id)
