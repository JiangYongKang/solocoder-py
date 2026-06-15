from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Any, Optional

from .exceptions import TokenizationError
from .models import TokenizationConfig


class TokenizationStrategy:
    def __init__(
        self,
        config: Optional[TokenizationConfig] = None,
        secret_key: Optional[bytes] = None,
    ) -> None:
        self._config: TokenizationConfig = config or TokenizationConfig()
        self._secret_key: bytes = secret_key or secrets.token_bytes(32)
        self._token_map: dict[str, str] = {}
        self._reverse_map: dict[str, str] = {}

    @property
    def config(self) -> TokenizationConfig:
        return self._config

    @property
    def secret_key(self) -> bytes:
        return self._secret_key

    def _generate_token(self, value: str) -> str:
        normalized_value = self._normalize_value(value)

        if normalized_value in self._token_map:
            return self._token_map[normalized_value]

        if self._config.use_hash:
            token = self._hash_based_token(normalized_value)
        else:
            token = self._random_token(normalized_value)

        self._token_map[normalized_value] = token
        self._reverse_map[token] = normalized_value

        return token

    def _normalize_value(self, value: Any) -> str:
        if value is None:
            return "__NONE__"
        if isinstance(value, str):
            if not value:
                return "__EMPTY__"
            return value
        return str(value)

    def _hash_based_token(self, value: str) -> str:
        hmac_obj = hmac.new(
            self._secret_key,
            value.encode("utf-8"),
            hashlib.sha256,
        )
        digest = hmac_obj.digest()

        encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

        token_length = self._config.token_length
        prefix = self._config.token_prefix

        if len(encoded) >= token_length:
            token_body = encoded[:token_length]
        else:
            extra = hashlib.sha256(digest).digest()
            extra_encoded = base64.urlsafe_b64encode(extra).rstrip(b"=").decode("ascii")
            combined = encoded + extra_encoded
            token_body = combined[:token_length]

        return prefix + token_body

    def _random_token(self, value: str) -> str:
        prefix = self._config.token_prefix
        token_length = self._config.token_length

        while True:
            random_bytes = secrets.token_bytes(token_length)
            token_body = (
                base64.urlsafe_b64encode(random_bytes)
                .rstrip(b"=")
                .decode("ascii")[:token_length]
            )
            token = prefix + token_body

            if token not in self._reverse_map:
                return token

    def tokenize(self, value: Any) -> str:
        return self._generate_token(value)

    def detokenize(self, token: str) -> Optional[str]:
        original = self._reverse_map.get(token)
        if original == "__NONE__":
            return None
        if original == "__EMPTY__":
            return ""
        return original

    def is_token(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return value in self._reverse_map

    def get_token_count(self) -> int:
        return len(self._token_map)

    def clear(self) -> None:
        self._token_map.clear()
        self._reverse_map.clear()

    def __call__(self, value: Any) -> str:
        return self.tokenize(value)

    def __contains__(self, value: Any) -> bool:
        normalized = self._normalize_value(value)
        return normalized in self._token_map


__all__ = [
    "TokenizationStrategy",
]
