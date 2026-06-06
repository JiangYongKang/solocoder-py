from datetime import datetime, timedelta

from solocoder_py.token import (
    AccessToken,
    RefreshToken,
    TokenFamily,
    TokenStatus,
)


class TestAccessToken:
    def test_is_active_true(self):
        now = datetime.now()
        token = AccessToken(
            token="abc",
            user_id="user-1",
            family_id="fam-1",
            issued_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        assert token.is_active is True

    def test_is_active_false_when_expired(self):
        now = datetime.now()
        token = AccessToken(
            token="abc",
            user_id="user-1",
            family_id="fam-1",
            issued_at=now - timedelta(minutes=30),
            expires_at=now - timedelta(minutes=15),
        )
        assert token.is_active is False

    def test_is_active_false_when_revoked(self):
        now = datetime.now()
        token = AccessToken(
            token="abc",
            user_id="user-1",
            family_id="fam-1",
            issued_at=now,
            expires_at=now + timedelta(minutes=15),
            status=TokenStatus.REVOKED,
        )
        assert token.is_active is False

    def test_is_expired_true(self):
        now = datetime.now()
        token = AccessToken(
            token="abc",
            user_id="user-1",
            family_id="fam-1",
            issued_at=now - timedelta(minutes=30),
            expires_at=now - timedelta(minutes=15),
        )
        assert token.is_expired is True

    def test_is_expired_false(self):
        now = datetime.now()
        token = AccessToken(
            token="abc",
            user_id="user-1",
            family_id="fam-1",
            issued_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        assert token.is_expired is False


class TestRefreshToken:
    def test_is_active_true(self):
        now = datetime.now()
        token = RefreshToken(
            token="abc",
            user_id="user-1",
            family_id="fam-1",
            generation=1,
            issued_at=now,
            expires_at=now + timedelta(days=7),
        )
        assert token.is_active is True

    def test_is_active_false_when_used(self):
        now = datetime.now()
        token = RefreshToken(
            token="abc",
            user_id="user-1",
            family_id="fam-1",
            generation=1,
            issued_at=now,
            expires_at=now + timedelta(days=7),
            status=TokenStatus.USED,
        )
        assert token.is_active is False


class TestTokenFamily:
    def test_revoke_all(self):
        now = datetime.now()
        family = TokenFamily(
            family_id="fam-1",
            user_id="user-1",
            created_at=now,
        )
        at = AccessToken(
            token="at-1",
            user_id="user-1",
            family_id="fam-1",
            issued_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        rt = RefreshToken(
            token="rt-1",
            user_id="user-1",
            family_id="fam-1",
            generation=1,
            issued_at=now,
            expires_at=now + timedelta(days=7),
        )
        family.access_tokens.append(at)
        family.generations.append(rt)

        family.revoke_all()

        assert family.revoked is True
        assert family.revoked_at is not None
        assert at.status == TokenStatus.REVOKED
        assert rt.status == TokenStatus.REVOKED
