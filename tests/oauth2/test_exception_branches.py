import threading
from datetime import timedelta

import pytest

from solocoder_py.oauth2 import (
    AuthorizationCodeAlreadyConsumedError,
    AuthorizationCodeExpiredError,
    AuthorizationCodeNotFoundError,
    AuthorizationSessionNotFoundError,
    CodeVerifierMismatchError,
    InvalidParameterError,
    OAuth2StateManager,
    StateInvalidError,
    StateMissingError,
    UnsupportedChallengeMethodError,
)
from .conftest import make_manager


class TestCodeVerifierMismatchRejected:
    def test_s256_verifier_mismatch_rejected(self):
        manager = make_manager()
        correct_verifier = "correct-verifier-s256"
        wrong_verifier = "wrong-verifier-s256"
        code_challenge = OAuth2StateManager.compute_s256_challenge(correct_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(session_id)

        with pytest.raises(CodeVerifierMismatchError):
            manager.consume_authorization_code(code, wrong_verifier)

    def test_plain_verifier_mismatch_rejected(self):
        manager = make_manager()
        correct_verifier = "correct-plain-verifier"
        wrong_verifier = "wrong-plain-verifier"

        session_id, state = manager.create_authorization_session(
            code_challenge=correct_verifier,
            code_challenge_method="plain",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(session_id)

        with pytest.raises(CodeVerifierMismatchError):
            manager.consume_authorization_code(code, wrong_verifier)

    def test_verify_pkce_standalone_mismatch(self):
        manager = make_manager()
        correct_verifier = "standalone-correct"
        wrong_verifier = "standalone-wrong"
        code_challenge = OAuth2StateManager.compute_s256_challenge(correct_verifier)

        session_id, _ = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        with pytest.raises(CodeVerifierMismatchError):
            manager.verify_pkce(session_id, wrong_verifier)


class TestStateMismatchRejected:
    def test_state_mismatch_rejected_on_verify(self):
        manager = make_manager()
        code_verifier = "state-mismatch-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, _ = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        with pytest.raises(StateInvalidError):
            manager.verify_state(session_id, "completely-wrong-state-value")


class TestConsumedAuthorizationCodeRejected:
    def test_already_consumed_code_rejected(self):
        manager = make_manager()
        code_verifier = "consumed-code-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(session_id)
        manager.consume_authorization_code(code, code_verifier)

        with pytest.raises(AuthorizationCodeAlreadyConsumedError):
            manager.consume_authorization_code(code, code_verifier)


class TestExpiredAuthorizationCodeRejected:
    def test_expired_code_rejected(self):
        from time import sleep

        manager = make_manager()
        code_verifier = "expired-code-verifier-2"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(
            session_id, expires_in=timedelta(milliseconds=30)
        )

        sleep(0.1)

        with pytest.raises(AuthorizationCodeExpiredError):
            manager.consume_authorization_code(code, code_verifier)


class TestUnknownAuthorizationCodeRejected:
    def test_unknown_code_rejected(self):
        manager = make_manager()
        with pytest.raises(AuthorizationCodeNotFoundError):
            manager.consume_authorization_code("unknown-code-xyz", "some-verifier")


class TestConcurrentConsumptionRaceProtection:
    def test_concurrent_consume_authorization_code_race(self):
        manager = make_manager()
        code_verifier = "concurrent-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(session_id)

        results = {}
        errors = []

        def consumer(consumer_id: int):
            try:
                result = manager.consume_authorization_code(code, code_verifier)
                results[consumer_id] = result
            except Exception as e:
                errors.append((consumer_id, type(e).__name__, str(e)))

        threads = [threading.Thread(target=consumer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(results) == 1
        assert len(errors) == 9
        assert all(
            err_type == "AuthorizationCodeAlreadyConsumedError"
            for _, err_type, _ in errors
        )


class TestUnsupportedChallengeMethodRejected:
    def test_unsupported_method_rejected_on_create(self):
        manager = make_manager()
        code_verifier = "test-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        with pytest.raises(UnsupportedChallengeMethodError):
            manager.create_authorization_session(
                code_challenge=code_challenge,
                code_challenge_method="MD5",
            )

    def test_unsupported_method_empty_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError):
            manager.create_authorization_session(
                code_challenge="some-challenge",
                code_challenge_method="",
            )

    def test_parse_code_challenge_method_unsupported(self):
        with pytest.raises(UnsupportedChallengeMethodError):
            OAuth2StateManager.parse_code_challenge_method("SHA1")

        with pytest.raises(InvalidParameterError):
            OAuth2StateManager.parse_code_challenge_method("")


class TestSessionNotFoundErrors:
    def test_verify_pkce_session_not_found(self):
        manager = make_manager()
        with pytest.raises(AuthorizationSessionNotFoundError):
            manager.verify_pkce("nonexistent-session", "any-verifier")

    def test_verify_state_session_not_found(self):
        manager = make_manager()
        with pytest.raises(AuthorizationSessionNotFoundError):
            manager.verify_state("nonexistent-session", "any-state")

    def test_generate_code_session_not_found(self):
        manager = make_manager()
        with pytest.raises(AuthorizationSessionNotFoundError):
            manager.generate_authorization_code("nonexistent-session")


class TestInvalidParameterErrors:
    def test_create_session_empty_challenge_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="code_challenge cannot be empty"):
            manager.create_authorization_session(
                code_challenge="",
                code_challenge_method="S256",
            )

    def test_consume_code_empty_code_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="authorization code cannot be empty"):
            manager.consume_authorization_code("", "any-verifier")

    def test_consume_code_empty_verifier_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="code_verifier cannot be empty"):
            manager.consume_authorization_code("any-code", "")

    def test_verify_pkce_empty_session_id_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="session_id cannot be empty"):
            manager.verify_pkce("", "any-verifier")

    def test_verify_pkce_empty_verifier_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="code_verifier cannot be empty"):
            manager.verify_pkce("any-session", "")

    def test_verify_state_empty_session_id_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="session_id cannot be empty"):
            manager.verify_state("", "any-state")

    def test_generate_code_empty_session_id_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="session_id cannot be empty"):
            manager.generate_authorization_code("")

    def test_generate_code_negative_expires_in_rejected(self):
        manager = make_manager()
        code_verifier = "negative-expiry-verifier"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, _ = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        with pytest.raises(InvalidParameterError, match="expires_in must be positive"):
            manager.generate_authorization_code(
                session_id, expires_in=timedelta(seconds=-1)
            )

    def test_invalid_manager_configuration_rejected(self):
        with pytest.raises(ValueError, match="default_code_expires_in must be positive"):
            OAuth2StateManager(default_code_expires_in=timedelta(seconds=0))

        with pytest.raises(ValueError, match="default_session_id_length must be positive"):
            OAuth2StateManager(default_session_id_length=0)

        with pytest.raises(ValueError, match="default_authorization_code_length must be positive"):
            OAuth2StateManager(default_authorization_code_length=0)

        with pytest.raises(ValueError, match="default_state_length must be positive"):
            OAuth2StateManager(default_state_length=0)


class TestAuthorizationSessionModelValidation:
    def test_session_empty_session_id_rejected(self):
        from solocoder_py.oauth2 import AuthorizationSession, CodeChallengeMethod

        with pytest.raises(ValueError, match="session_id cannot be empty"):
            AuthorizationSession(
                session_id="",
                code_challenge="challenge",
                code_challenge_method=CodeChallengeMethod.S256,
            )

    def test_session_empty_code_challenge_rejected(self):
        from solocoder_py.oauth2 import AuthorizationSession, CodeChallengeMethod

        with pytest.raises(ValueError, match="code_challenge cannot be empty"):
            AuthorizationSession(
                session_id="session-1",
                code_challenge="",
                code_challenge_method=CodeChallengeMethod.S256,
            )

    def test_session_invalid_code_challenge_method_rejected(self):
        from solocoder_py.oauth2 import AuthorizationSession

        with pytest.raises(ValueError, match="code_challenge_method must be a CodeChallengeMethod enum"):
            AuthorizationSession(
                session_id="session-1",
                code_challenge="challenge",
                code_challenge_method="plain",
            )


class TestGetSessionInvalidParameters:
    def test_get_session_empty_session_id_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="session_id cannot be empty"):
            manager.get_session("")

    def test_get_session_by_code_empty_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="authorization code cannot be empty"):
            manager.get_session_by_code("")

    def test_invalidate_session_empty_rejected(self):
        manager = make_manager()
        with pytest.raises(InvalidParameterError, match="session_id cannot be empty"):
            manager.invalidate_session("")


class TestCleanupExpired:
    def test_cleanup_expired_sessions(self):
        from time import sleep

        manager = make_manager()

        code_verifier_1 = "cleanup-verifier-1"
        code_challenge_1 = OAuth2StateManager.compute_s256_challenge(code_verifier_1)
        session_id_1, _ = manager.create_authorization_session(
            code_challenge=code_challenge_1,
            code_challenge_method="S256",
        )
        manager.generate_authorization_code(
            session_id_1, expires_in=timedelta(milliseconds=30)
        )

        code_verifier_2 = "cleanup-verifier-2"
        code_challenge_2 = OAuth2StateManager.compute_s256_challenge(code_verifier_2)
        session_id_2, _ = manager.create_authorization_session(
            code_challenge=code_challenge_2,
            code_challenge_method="S256",
        )
        manager.generate_authorization_code(
            session_id_2, expires_in=timedelta(minutes=10)
        )

        assert manager.count_sessions() == 2

        sleep(0.1)

        cleaned = manager.cleanup_expired()
        assert cleaned == 1
        assert manager.count_sessions() == 1
        assert manager.get_session(session_id_1) is None
        assert manager.get_session(session_id_2) is not None
