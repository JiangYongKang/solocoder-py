from __future__ import annotations

from typing import Optional

from .models import AccessToken, RefreshToken, TokenFamily


class TokenRepository:
    def __init__(self) -> None:
        self._families: dict[str, TokenFamily] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}

    def save_family(self, family: TokenFamily) -> None:
        self._families[family.family_id] = family

    def get_family(self, family_id: str) -> Optional[TokenFamily]:
        return self._families.get(family_id)

    def save_access_token(self, token: AccessToken) -> None:
        self._access_tokens[token.token] = token
        family = self._families.get(token.family_id)
        if family is not None and token not in family.access_tokens:
            family.access_tokens.append(token)

    def get_access_token(self, token_str: str) -> Optional[AccessToken]:
        return self._access_tokens.get(token_str)

    def save_refresh_token(self, token: RefreshToken) -> None:
        self._refresh_tokens[token.token] = token
        family = self._families.get(token.family_id)
        if family is not None:
            if token.generation > family.latest_generation:
                family.latest_generation = token.generation
            exists = any(rt.token == token.token for rt in family.generations)
            if not exists:
                family.generations.append(token)

    def get_refresh_token(self, token_str: str) -> Optional[RefreshToken]:
        return self._refresh_tokens.get(token_str)

    def revoke_family(self, family_id: str) -> None:
        family = self._families.get(family_id)
        if family is not None:
            family.revoke_all()
