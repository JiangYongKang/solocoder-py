import pytest

from solocoder_py.session_store import (
    InvalidSessionConfigError,
    InvalidSessionIdError,
    InvalidUserIdError,
    SessionCreateConfig,
    SessionExpiredError,
    SessionForciblyLoggedOutError,
    SessionIdleTimeoutError,
    SessionLimitExceededError,
    SessionNotFoundError,
    SessionStore,
)

from .conftest import FakeClock, make_config, make_store


class TestSessionNotFound:
    def test_get_nonexistent_session(self):
        store = make_store()
        with pytest.raises(SessionNotFoundError, match="not found"):
            store.get_session("nonexistent")

    def test_update_nonexistent_session(self):
        store = make_store()
        with pytest.raises(SessionNotFoundError, match="not found"):
            store.update_session("nonexistent", {"k": "v"})

    def test_get_empty_session_id(self):
        store = make_store()
        with pytest.raises(InvalidSessionIdError):
            store.get_session("")

    def test_get_none_session_id(self):
        store = make_store()
        with pytest.raises(InvalidSessionIdError):
            store.get_session(None)

    def test_update_empty_session_id(self):
        store = make_store()
        with pytest.raises(InvalidSessionIdError):
            store.update_session("", {"k": "v"})


class TestSessionExpired:
    def test_access_expired_session_ttl(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=10.0, idle_timeout=10.0)
        session = store.create_session("user-1", config=config)

        clock.advance(11.0)
        with pytest.raises(SessionExpiredError, match="expired"):
            store.get_session(session.session_id)

    def test_update_expired_session_ttl(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=10.0, idle_timeout=10.0)
        session = store.create_session("user-1", config=config)

        clock.advance(11.0)
        with pytest.raises(SessionExpiredError, match="expired"):
            store.update_session(session.session_id, {"k": "v"})

    def test_expired_session_removed_from_store(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=10.0, idle_timeout=10.0)
        session = store.create_session("user-1", config=config)

        clock.advance(11.0)
        with pytest.raises(SessionExpiredError):
            store.get_session(session.session_id)

        with pytest.raises(SessionNotFoundError):
            store.get_session(session.session_id)


class TestSessionIdleTimeout:
    def test_access_idle_timed_out_session(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=10.0)
        session = store.create_session("user-1", config=config)

        clock.advance(11.0)
        with pytest.raises(SessionIdleTimeoutError, match="inactivity"):
            store.get_session(session.session_id)

    def test_update_idle_timed_out_session(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=10.0)
        session = store.create_session("user-1", config=config)

        clock.advance(11.0)
        with pytest.raises(SessionIdleTimeoutError, match="inactivity"):
            store.update_session(session.session_id, {"k": "v"})

    def test_idle_timeout_removed_from_store(self):
        clock = FakeClock()
        store = make_store(clock=clock)
        config = make_config(ttl=3600.0, idle_timeout=10.0)
        session = store.create_session("user-1", config=config)

        clock.advance(11.0)
        with pytest.raises(SessionIdleTimeoutError):
            store.get_session(session.session_id)

        with pytest.raises(SessionNotFoundError):
            store.get_session(session.session_id)


class TestSessionForciblyLoggedOut:
    def test_access_evicted_session(self):
        store = make_store()
        from solocoder_py.session_store import EvictionStrategy

        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        s1 = store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError) as exc:
            store.get_session(s1.session_id)
        assert "evicted" in str(exc.value)

    def test_update_evicted_session(self):
        store = make_store()
        from solocoder_py.session_store import EvictionStrategy

        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        s1 = store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError):
            store.update_session(s1.session_id, {"k": "v"})

    def test_logout_all_then_access(self):
        store = make_store()
        config = make_config(max_concurrent_sessions=10)
        session = store.create_session("user-1", config=config)
        store.logout_all_sessions("user-1", reason="security breach")

        with pytest.raises(SessionForciblyLoggedOutError) as exc:
            store.get_session(session.session_id)
        assert "security breach" in str(exc.value)

    def test_evicted_session_specific_error_message(self):
        store = make_store()
        from solocoder_py.session_store import EvictionStrategy

        config = make_config(
            max_concurrent_sessions=1,
            eviction_strategy=EvictionStrategy.EVICT_OLDEST,
        )
        s1 = store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)

        with pytest.raises(SessionForciblyLoggedOutError) as exc:
            store.get_session(s1.session_id)
        assert "concurrent session limit" in str(exc.value)


class TestInvalidConfig:
    def test_ttl_less_than_idle_timeout_rejected_config(self):
        with pytest.raises(
            InvalidSessionConfigError, match="idle_timeout must be less than or equal to ttl"
        ):
            make_config(ttl=10.0, idle_timeout=20.0)

    def test_ttl_less_than_idle_timeout_rejected_on_create(self):
        store = make_store()
        invalid_config = SessionCreateConfig(
            ttl=3600.0, idle_timeout=1800.0, max_concurrent_sessions=5
        )
        invalid_config.idle_timeout = 7200.0

        with pytest.raises(InvalidSessionConfigError):
            store.create_session("user-1", config=invalid_config)

    def test_negative_ttl_rejected(self):
        with pytest.raises(InvalidSessionConfigError, match="ttl must be positive"):
            make_config(ttl=-1.0, idle_timeout=10.0)

    def test_zero_ttl_rejected(self):
        with pytest.raises(InvalidSessionConfigError, match="ttl must be positive"):
            make_config(ttl=0.0, idle_timeout=10.0)

    def test_negative_idle_timeout_rejected(self):
        with pytest.raises(
            InvalidSessionConfigError, match="idle_timeout must be positive"
        ):
            make_config(ttl=100.0, idle_timeout=-5.0)

    def test_zero_idle_timeout_rejected(self):
        with pytest.raises(
            InvalidSessionConfigError, match="idle_timeout must be positive"
        ):
            make_config(ttl=100.0, idle_timeout=0.0)

    def test_negative_max_concurrent_sessions_rejected(self):
        with pytest.raises(
            InvalidSessionConfigError,
            match="max_concurrent_sessions must be positive",
        ):
            make_config(ttl=100.0, idle_timeout=50.0, max_concurrent_sessions=-1)

    def test_zero_max_concurrent_sessions_rejected(self):
        with pytest.raises(
            InvalidSessionConfigError,
            match="max_concurrent_sessions must be positive",
        ):
            make_config(ttl=100.0, idle_timeout=50.0, max_concurrent_sessions=0)

    def test_store_init_with_invalid_config(self):
        invalid_config = SessionCreateConfig(
            ttl=100.0, idle_timeout=50.0, max_concurrent_sessions=5
        )
        invalid_config.ttl = -10.0

        with pytest.raises(InvalidSessionConfigError):
            SessionStore(default_config=invalid_config)

    def test_session_model_ttl_less_than_idle(self):
        from solocoder_py.session_store import Session

        with pytest.raises(InvalidSessionConfigError, match="idle_timeout must be less than or equal to ttl"):
            Session(
                session_id="sess_test",
                user_id="user-1",
                created_at=1000.0,
                expires_at=1010.0,
                idle_expires_at=1020.0,
                ttl=10.0,
                idle_timeout=20.0,
            )


class TestInvalidUserId:
    def test_empty_user_id_create_rejected(self):
        store = make_store()
        with pytest.raises(InvalidUserIdError, match="non-empty string"):
            store.create_session("", {"k": "v"})

    def test_whitespace_user_id_create_rejected(self):
        store = make_store()
        with pytest.raises(InvalidUserIdError, match="non-empty string"):
            store.create_session("   ", {"k": "v"})

    def test_none_user_id_create_rejected(self):
        store = make_store()
        with pytest.raises(InvalidUserIdError):
            store.create_session(None, {"k": "v"})

    def test_empty_user_id_list_rejected(self):
        store = make_store()
        with pytest.raises(InvalidUserIdError, match="non-empty string"):
            store.list_sessions_by_user("")

    def test_empty_user_id_logout_all_rejected(self):
        store = make_store()
        with pytest.raises(InvalidUserIdError, match="non-empty string"):
            store.logout_all_sessions("")

    def test_numeric_user_id_create_rejected(self):
        store = make_store()
        with pytest.raises(InvalidUserIdError):
            store.create_session(123, {"k": "v"})


class TestSessionLimitExceeded:
    def test_reject_strategy_at_limit(self):
        store = make_store()
        from solocoder_py.session_store import EvictionStrategy

        config = make_config(
            max_concurrent_sessions=3,
            eviction_strategy=EvictionStrategy.REJECT,
        )
        for i in range(3):
            store.create_session("user-1", config=config)

        with pytest.raises(SessionLimitExceededError, match="exceeded"):
            store.create_session("user-1", config=config)

    def test_reject_does_not_affect_other_users(self):
        store = make_store()
        from solocoder_py.session_store import EvictionStrategy

        config = make_config(
            max_concurrent_sessions=2,
            eviction_strategy=EvictionStrategy.REJECT,
        )
        store.create_session("user-1", config=config)
        store.create_session("user-1", config=config)

        store.create_session("user-2", config=config)
        store.create_session("user-2", config=config)

        with pytest.raises(SessionLimitExceededError):
            store.create_session("user-1", config=config)

        info = store.create_session("user-3", config=config)
        assert info.user_id == "user-3"


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(SessionNotFoundError, Exception)
        assert issubclass(SessionExpiredError, Exception)
        assert issubclass(SessionIdleTimeoutError, Exception)
        assert issubclass(SessionForciblyLoggedOutError, Exception)
        assert issubclass(SessionLimitExceededError, Exception)
        assert issubclass(InvalidSessionConfigError, Exception)
        assert issubclass(InvalidUserIdError, Exception)

    def test_session_create_config_validation(self):
        with pytest.raises(InvalidSessionConfigError, match="ttl must be positive"):
            SessionCreateConfig(ttl=0, idle_timeout=10)

        with pytest.raises(InvalidSessionConfigError, match="idle_timeout must be positive"):
            SessionCreateConfig(ttl=100, idle_timeout=0)

        with pytest.raises(InvalidSessionConfigError, match="idle_timeout must be less than or equal to ttl"):
            SessionCreateConfig(ttl=10, idle_timeout=20)

        with pytest.raises(InvalidSessionConfigError, match="max_concurrent_sessions must be positive"):
            SessionCreateConfig(ttl=100, idle_timeout=50, max_concurrent_sessions=0)
