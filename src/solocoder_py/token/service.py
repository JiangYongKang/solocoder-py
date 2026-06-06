from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .models import (
    AccessToken,
    RefreshToken,
    TokenFamily,
    TokenPair,
    TokenStatus,
)
from .repository import TokenRepository


class TokenError(Exception):
    pass


class TokenExpiredError(TokenError):
    pass


class TokenRevokedError(TokenError):
    pass


class TokenReusedError(TokenError):
    pass


class TokenNotFoundError(TokenError):
    pass


class TokenService:
    def __init__(
        self,
        repository: Optional[TokenRepository] = None,
        access_token_ttl: timedelta = timedelta(minutes=15),
        refresh_token_ttl: timedelta = timedelta(days=7),
    ) -> None:
        if access_token_ttl <= timedelta(0):
            raise ValueError("access_token_ttl must be a positive timedelta")
        if refresh_token_ttl <= timedelta(0):
            raise ValueError("refresh_token_ttl must be a positive timedelta")
        self._repo = repository or TokenRepository()
        self._access_token_ttl = access_token_ttl
        self._refresh_token_ttl = refresh_token_ttl

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_urlsafe(32)

    def issue_token_pair(self, user_id: str) -> TokenPair:
        now = datetime.now()
        family_id = str(uuid.uuid4())

        family = TokenFamily(
            family_id=family_id,
            user_id=user_id,
            created_at=now,
        )
        self._repo.save_family(family)

        access_token = AccessToken(
            token=self._generate_token(),
            user_id=user_id,
            family_id=family_id,
            issued_at=now,
            expires_at=now + self._access_token_ttl,
        )
        self._repo.save_access_token(access_token)

        refresh_token = RefreshToken(
            token=self._generate_token(),
            user_id=user_id,
            family_id=family_id,
            generation=1,
            issued_at=now,
            expires_at=now + self._refresh_token_ttl,
        )
        self._repo.save_refresh_token(refresh_token)

        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def refresh_token_pair(self, refresh_token_str: str) -> TokenPair:
        old_refresh = self._repo.get_refresh_token(refresh_token_str)
        if old_refresh is None:
            raise TokenNotFoundError("Refresh token not found")

        family = self._repo.get_family(old_refresh.family_id)
        if family is None:
            raise TokenNotFoundError("Token family not found")

        if family.revoked:
            raise TokenRevokedError("Token family has been revoked")

        if old_refresh.status != TokenStatus.ACTIVE:
            family.revoke_all()
            raise TokenReusedError(
                "Refresh token reuse detected. Entire token family revoked."
            )

        if old_refresh.is_expired:
            old_refresh.status = TokenStatus.EXPIRED
            raise TokenExpiredError("Refresh token has expired")

        old_refresh.status = TokenStatus.USED

        now = datetime.now()
        new_generation = old_refresh.generation + 1

        new_access = AccessToken(
            token=self._generate_token(),
            user_id=old_refresh.user_id,
            family_id=old_refresh.family_id,
            issued_at=now,
            expires_at=now + self._access_token_ttl,
        )
        self._repo.save_access_token(new_access)

        new_refresh = RefreshToken(
            token=self._generate_token(),
            user_id=old_refresh.user_id,
            family_id=old_refresh.family_id,
            generation=new_generation,
            issued_at=now,
            expires_at=now + self._refresh_token_ttl,
        )
        self._repo.save_refresh_token(new_refresh)

        return TokenPair(access_token=new_access, refresh_token=new_refresh)

    def validate_access_token(self, token_str: str) -> AccessToken:
        access_token = self._repo.get_access_token(token_str)
        if access_token is None:
            raise TokenNotFoundError("Access token not found")

        family = self._repo.get_family(access_token.family_id)
        if family is not None and family.revoked:
            raise TokenRevokedError("Token family has been revoked")

        if access_token.status == TokenStatus.REVOKED:
            raise TokenRevokedError("Access token has been revoked")

        if access_token.status == TokenStatus.USED:
            raise TokenRevokedError("Access token has been used")

        if access_token.status == TokenStatus.EXPIRED or access_token.is_expired:
            access_token.status = TokenStatus.EXPIRED
            raise TokenExpiredError("Access token has expired")

        return access_token

    def revoke_family_by_refresh_token(self, refresh_token_str: str) -> None:
        refresh_token = self._repo.get_refresh_token(refresh_token_str)
        if refresh_token is None:
            raise TokenNotFoundError("Refresh token not found")
        self._repo.revoke_family(refresh_token.family_id)

    def revoke_family(self, family_id: str) -> None:
        family = self._repo.get_family(family_id)
        if family is None:
            raise TokenNotFoundError("Token family not found")
        self._repo.revoke_family(family_id)
