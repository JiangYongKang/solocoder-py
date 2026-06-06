import time
from datetime import timedelta

import pytest

from solocoder_py.token import (
    TokenError,
    TokenExpiredError,
    TokenNotFoundError,
    TokenReusedError,
    TokenRevokedError,
    TokenRepository,
    TokenService,
    TokenStatus,
)


class TestIssueTokenPair:
    def test_issue_token_pair_returns_tokens(self, service: TokenService):
        pair = service.issue_token_pair("user-1")

        assert pair.access_token is not None
        assert pair.refresh_token is not None
        assert pair.access_token.user_id == "user-1"
        assert pair.refresh_token.user_id == "user-1"

    def test_tokens_are_random_and_unique(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.issue_token_pair("user-1")

        assert pair1.access_token.token != pair2.access_token.token
        assert pair1.refresh_token.token != pair2.refresh_token.token
        assert pair1.access_token.family_id != pair2.access_token.family_id

    def test_tokens_have_correct_expiry(self, service: TokenService):
        pair = service.issue_token_pair("user-1")

        assert pair.access_token.expires_at > pair.access_token.issued_at
        assert pair.refresh_token.expires_at > pair.refresh_token.issued_at
        assert (
            pair.refresh_token.expires_at - pair.refresh_token.issued_at
        ) > (pair.access_token.expires_at - pair.access_token.issued_at)

    def test_refresh_token_generation_starts_at_one(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        assert pair.refresh_token.generation == 1

    def test_tokens_belong_to_same_family(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        assert pair.access_token.family_id == pair.refresh_token.family_id

    def test_token_strings_are_not_empty(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        assert len(pair.access_token.token) > 0
        assert len(pair.refresh_token.token) > 0


class TestValidateAccessToken:
    def test_validate_valid_access_token(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        validated = service.validate_access_token(pair.access_token.token)
        assert validated.user_id == "user-1"
        assert validated.token == pair.access_token.token

    def test_validate_unknown_token_raises(self, service: TokenService):
        with pytest.raises(TokenNotFoundError):
            service.validate_access_token("nonexistent-token")

    def test_validate_expired_access_token_raises(self, short_ttl_service: TokenService):
        pair = short_ttl_service.issue_token_pair("user-1")
        time.sleep(0.1)
        with pytest.raises(TokenExpiredError):
            short_ttl_service.validate_access_token(pair.access_token.token)

    def test_validate_revoked_family_access_token_raises(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        service.revoke_family(pair.access_token.family_id)
        with pytest.raises(TokenRevokedError):
            service.validate_access_token(pair.access_token.token)


class TestRefreshTokenPair:
    def test_refresh_returns_new_token_pair(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)

        assert pair2.access_token.token != pair1.access_token.token
        assert pair2.refresh_token.token != pair1.refresh_token.token
        assert pair2.access_token.user_id == "user-1"
        assert pair2.refresh_token.user_id == "user-1"

    def test_refresh_increments_generation(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)
        pair3 = service.refresh_token_pair(pair2.refresh_token.token)

        assert pair1.refresh_token.generation == 1
        assert pair2.refresh_token.generation == 2
        assert pair3.refresh_token.generation == 3

    def test_refresh_maintains_family_id(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)
        pair3 = service.refresh_token_pair(pair2.refresh_token.token)

        family_id = pair1.access_token.family_id
        assert pair2.access_token.family_id == family_id
        assert pair2.refresh_token.family_id == family_id
        assert pair3.access_token.family_id == family_id
        assert pair3.refresh_token.family_id == family_id

    def test_old_refresh_token_becomes_used_after_refresh(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        old_rt_token = pair1.refresh_token.token
        service.refresh_token_pair(old_rt_token)

        refreshed = service._repo.get_refresh_token(old_rt_token)
        assert refreshed is not None
        assert refreshed.status == TokenStatus.USED

    def test_refresh_unknown_token_raises(self, service: TokenService):
        with pytest.raises(TokenNotFoundError):
            service.refresh_token_pair("nonexistent-token")

    def test_refresh_expired_refresh_token_raises(
        self, short_ttl_service: TokenService
    ):
        pair = short_ttl_service.issue_token_pair("user-1")
        rt_token = pair.refresh_token.token
        time.sleep(0.1)
        with pytest.raises(TokenExpiredError):
            short_ttl_service.refresh_token_pair(rt_token)

        refreshed = short_ttl_service._repo.get_refresh_token(rt_token)
        assert refreshed is not None
        assert refreshed.status == TokenStatus.EXPIRED


class TestTokenReuseDetection:
    def test_reusing_old_refresh_token_revokes_family(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)

        with pytest.raises(TokenReusedError):
            service.refresh_token_pair(pair1.refresh_token.token)

        family = service._repo.get_family(pair1.access_token.family_id)
        assert family is not None
        assert family.revoked is True

    def test_after_reuse_new_tokens_are_revoked(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)

        with pytest.raises(TokenReusedError):
            service.refresh_token_pair(pair1.refresh_token.token)

        with pytest.raises(TokenRevokedError):
            service.validate_access_token(pair2.access_token.token)

    def test_after_reuse_attempting_refresh_with_latest_fails(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)

        with pytest.raises(TokenReusedError):
            service.refresh_token_pair(pair1.refresh_token.token)

        with pytest.raises(TokenRevokedError):
            service.refresh_token_pair(pair2.refresh_token.token)

    def test_reuse_detected_across_multiple_generations(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)
        pair3 = service.refresh_token_pair(pair2.refresh_token.token)
        pair4 = service.refresh_token_pair(pair3.refresh_token.token)

        with pytest.raises(TokenReusedError):
            service.refresh_token_pair(pair2.refresh_token.token)

        family = service._repo.get_family(pair1.access_token.family_id)
        assert family is not None
        assert family.revoked is True

        for rt in family.generations:
            assert rt.status == TokenStatus.REVOKED

        for at in family.access_tokens:
            assert at.status == TokenStatus.REVOKED

        with pytest.raises(TokenRevokedError):
            service.validate_access_token(pair4.access_token.token)


class TestRevokeFamily:
    def test_revoke_family_by_id(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        service.revoke_family(pair.access_token.family_id)

        family = service._repo.get_family(pair.access_token.family_id)
        assert family is not None
        assert family.revoked is True

    def test_revoke_family_by_refresh_token(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        service.revoke_family_by_refresh_token(pair.refresh_token.token)

        family = service._repo.get_family(pair.access_token.family_id)
        assert family is not None
        assert family.revoked is True

    def test_revoke_unknown_family_raises(self, service: TokenService):
        with pytest.raises(TokenNotFoundError):
            service.revoke_family("nonexistent-family")

    def test_revoke_unknown_refresh_token_raises(self, service: TokenService):
        with pytest.raises(TokenNotFoundError):
            service.revoke_family_by_refresh_token("nonexistent-token")

    def test_cannot_refresh_revoked_family(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        service.revoke_family(pair.access_token.family_id)

        with pytest.raises(TokenRevokedError):
            service.refresh_token_pair(pair.refresh_token.token)


class TestMultipleRotations:
    def test_consecutive_rotations_maintain_family(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        family_id = pair.access_token.family_id

        for i in range(10):
            pair = service.refresh_token_pair(pair.refresh_token.token)
            assert pair.access_token.family_id == family_id
            assert pair.refresh_token.family_id == family_id
            assert pair.refresh_token.generation == i + 2

        family = service._repo.get_family(family_id)
        assert family is not None
        assert len(family.generations) == 11
        assert len(family.access_tokens) == 11
        assert family.latest_generation == 11

    def test_only_latest_refresh_token_is_active(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        tokens = [pair.refresh_token.token]

        for _ in range(5):
            pair = service.refresh_token_pair(pair.refresh_token.token)
            tokens.append(pair.refresh_token.token)

        for i, token in enumerate(tokens):
            rt = service._repo.get_refresh_token(token)
            assert rt is not None
            if i == len(tokens) - 1:
                assert rt.status == TokenStatus.ACTIVE
            else:
                assert rt.status == TokenStatus.USED


class TestErrorHierarchy:
    def test_token_errors_inherit_from_token_error(self):
        assert issubclass(TokenExpiredError, TokenError)
        assert issubclass(TokenRevokedError, TokenError)
        assert issubclass(TokenReusedError, TokenError)
        assert issubclass(TokenNotFoundError, TokenError)


class TestTokenServiceTTLValidation:
    def test_zero_access_token_ttl_raises(self, repo: TokenRepository):
        with pytest.raises(ValueError, match="access_token_ttl must be a positive timedelta"):
            TokenService(repository=repo, access_token_ttl=timedelta(0))

    def test_negative_access_token_ttl_raises(self, repo: TokenRepository):
        with pytest.raises(ValueError, match="access_token_ttl must be a positive timedelta"):
            TokenService(repository=repo, access_token_ttl=timedelta(seconds=-1))

    def test_zero_refresh_token_ttl_raises(self, repo: TokenRepository):
        with pytest.raises(ValueError, match="refresh_token_ttl must be a positive timedelta"):
            TokenService(repository=repo, refresh_token_ttl=timedelta(0))

    def test_negative_refresh_token_ttl_raises(self, repo: TokenRepository):
        with pytest.raises(ValueError, match="refresh_token_ttl must be a positive timedelta"):
            TokenService(repository=repo, refresh_token_ttl=timedelta(days=-1))

    def test_valid_ttl_does_not_raise(self, repo: TokenRepository):
        service = TokenService(
            repository=repo,
            access_token_ttl=timedelta(seconds=1),
            refresh_token_ttl=timedelta(seconds=1),
        )
        assert service is not None


class TestValidateAccessTokenUsedState:
    def test_validate_used_access_token_raises(self, service: TokenService):
        pair = service.issue_token_pair("user-1")
        access = service._repo.get_access_token(pair.access_token.token)
        assert access is not None
        access.status = TokenStatus.USED

        with pytest.raises(TokenRevokedError):
            service.validate_access_token(pair.access_token.token)

    def test_validate_expired_access_token_marks_expired(self, short_ttl_service: TokenService):
        pair = short_ttl_service.issue_token_pair("user-1")
        at_token = pair.access_token.token
        time.sleep(0.1)
        with pytest.raises(TokenExpiredError):
            short_ttl_service.validate_access_token(at_token)

        access = short_ttl_service._repo.get_access_token(at_token)
        assert access is not None
        assert access.status == TokenStatus.EXPIRED


class TestReuseDetectionWithExpiredUsedToken:
    def test_used_refresh_token_after_expiry_triggers_revoke(self, service: TokenService):
        pair1 = service.issue_token_pair("user-1")
        pair2 = service.refresh_token_pair(pair1.refresh_token.token)

        old_rt = service._repo.get_refresh_token(pair1.refresh_token.token)
        assert old_rt is not None
        assert old_rt.status == TokenStatus.USED

        old_rt.expires_at = old_rt.issued_at - timedelta(days=1)

        with pytest.raises(TokenReusedError):
            service.refresh_token_pair(pair1.refresh_token.token)

        family = service._repo.get_family(pair1.access_token.family_id)
        assert family is not None
        assert family.revoked is True

        with pytest.raises(TokenRevokedError):
            service.validate_access_token(pair2.access_token.token)
