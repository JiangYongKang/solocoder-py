from datetime import timedelta
from time import sleep

import pytest

from solocoder_py.oauth2 import (
    AuthorizationCodeAlreadyConsumedError,
    OAuth2StateManager,
)
from .conftest import make_manager


class TestPKCES256VerificationSuccess:
    def test_s256_challenge_verification_success(self):
        manager = make_manager()
        code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        assert session_id is not None
        assert state is not None

        manager.verify_pkce(session_id, code_verifier)

    def test_s256_compute_challenge_known_vector(self):
        code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        result = OAuth2StateManager.compute_s256_challenge(code_verifier)
        assert result == expected_challenge


class TestStateVerificationConsistency:
    def test_state_verification_consistent(self):
        manager = make_manager()
        code_verifier = "test-verifier-xyz"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        manager.verify_state(session_id, state)

        session = manager.get_session(session_id)
        assert session is not None
        assert session.state_verified is True
        assert session.state_consumed is True


class TestAuthorizationCodeSingleUse:
    def test_authorization_code_consumed_once_not_reusable(self):
        manager = make_manager()
        code_verifier = "test-verifier-single-use"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(session_id)
        assert code is not None

        consumed_session = manager.consume_authorization_code(code, code_verifier)
        assert consumed_session is not None
        assert consumed_session.authorization_code == code
        assert consumed_session.authorization_code_consumed is True

        with pytest.raises(AuthorizationCodeAlreadyConsumedError):
            manager.consume_authorization_code(code, code_verifier)


class TestFullAuthorizationFlow:
    def test_full_authorization_flow_s256(self):
        manager = make_manager()
        code_verifier = "full-flow-verifier-s256"
        code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

        session_id, state = manager.create_authorization_session(
            code_challenge=code_challenge,
            code_challenge_method="S256",
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            scope="read write",
        )

        manager.verify_state(session_id, state)

        code = manager.generate_authorization_code(
            session_id, expires_in=timedelta(minutes=5)
        )

        session = manager.get_session(session_id)
        assert session is not None
        assert session.authorization_code == code
        assert session.authorization_code_created_at is not None
        assert session.authorization_code_expires_at is not None

        consumed = manager.consume_authorization_code(code, code_verifier)
        assert consumed.session_id == session_id
        assert consumed.client_id == "test-client"
        assert consumed.redirect_uri == "https://example.com/callback"
        assert consumed.scope == "read write"
        assert consumed.authorization_code_consumed is True
