from datetime import timedelta
from time import sleep

import pytest

from solocoder_py.oauth2 import (
    AuthorizationCodeExpiredError,
    InvalidParameterError,
    OAuth2StateManager,
    StateMissingError,
)
from .conftest import make_manager


class TestPKCEPlainModeVerification:
    def test_plain_challenge_verification_success(self):
        manager = make_manager()
        code_verifier = "test-plain-verifier-string-12345"
        code_challenge = code_verifier

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="plain",
        )

        manager.verify_pkce(session_id, code_verifier)

    def test_plain_mode_consume_code_success(self):
        manager = make_manager()
        code_verifier = "plain-mode-consume-verifier"
        code_challenge = code_verifier

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="plain",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(session_id)
        consumed = manager.consume_authorization_code(code, code_verifier)
        assert consumed.session_id == session_id


class TestStateParameterEmptyRejected:
    def test_empty_state_rejected_on_create(self):
        manager = make_manager()
        code_verifier = "test-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        with pytest.raises(InvalidParameterError, match="state cannot be empty"):
            manager.create_authorization_session(
                code_challenge=code_challenge,
                code_challenge_method="S256",
                state="",
                auto_generate_state=False,
            )

    def test_none_state_without_auto_generate_rejected(self):
        manager = make_manager()
        code_verifier = "test-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        with pytest.raises(InvalidParameterError, match="state cannot be empty"):
            manager.create_authorization_session(
                code_challenge=code_challenge,
                code_challenge_method="S256",
                state=None,
                auto_generate_state=False,
            )

    def test_empty_state_rejected_on_verify(self):
        manager = make_manager()
        code_verifier = "test-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, _ = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        with pytest.raises(StateMissingError, match="state parameter is missing or empty"):
            manager.verify_state(session_id, "")


class TestAuthorizationCodeJustExpiredRejected:
    def test_authorization_code_expired_rejected(self):
        manager = make_manager()
        code_verifier = "expired-code-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(
            session_id, expires_in=timedelta(milliseconds=50)
        )

        sleep(0.1)

        with pytest.raises(AuthorizationCodeExpiredError):
            manager.consume_authorization_code(code, code_verifier)

    def test_authorization_code_at_boundary_not_expired(self):
        manager = make_manager()
        code_verifier = "boundary-code-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(
            session_id, expires_in=timedelta(seconds=2)
        )

        sleep(0.05)

        consumed = manager.consume_authorization_code(code, code_verifier)
        assert consumed is not None
        assert consumed.authorization_code_consumed is True


class TestStateOneTimeUse:
    def test_state_can_only_be_verified_once(self):
        from solocoder_py.oauth2 import StateAlreadyUsedError

        manager = make_manager()
        code_verifier = "state-one-time-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        manager.verify_state(session_id, state)

        with pytest.raises(StateAlreadyUsedError):
            manager.verify_state(session_id, state)


class TestSessionManagementBoundary:
    def test_get_session_nonexistent_returns_none(self):
        manager = make_manager()
        assert manager.get_session("nonexistent-session-id") is None

    def test_get_session_by_code_nonexistent_returns_none(self):
        manager = make_manager()
        assert manager.get_session_by_code("nonexistent-code") is None

    def test_invalidate_session_existing(self):
        manager = make_manager()
        code_verifier = "invalidate-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, _ = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        assert manager.count_sessions() == 1

        result = manager.invalidate_session(session_id)
        assert result is True
        assert manager.count_sessions() == 0
        assert manager.get_session(session_id) is None

    def test_invalidate_session_nonexistent(self):
        manager = make_manager()
        result = manager.invalidate_session("nonexistent-session")
        assert result is False

    def test_clear_all_sessions(self):
        manager = make_manager()
        for i in range(5):
            code_verifier = f"verifier-{i}"
            code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)
            manager.create_authorization_session(
                code_challenge=code_challenge,
                code_challenge_method="S256",
            )
        assert manager.count_sessions() == 5
        manager.clear()
        assert manager.count_sessions() == 0
