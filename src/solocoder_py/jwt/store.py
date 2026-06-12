from __future__ import annotations

import threading
from typing import Optional

from .exceptions import EmptyKeyStoreError, KeyNotFoundError
from .models import (
    JWTClock,
    JWTConfig,
    SigningKey,
    _generate_kid,
    _generate_secret,
)


class KeyStore:
    def __init__(
        self,
        config: JWTConfig,
        clock: Optional[JWTClock] = None,
    ) -> None:
        self._config: JWTConfig = config
        self._clock: JWTClock = clock or JWTClock()
        self._keys: dict[str, SigningKey] = {}
        self._active_kid: Optional[str] = None
        self._lock: threading.RLock = threading.RLock()

    @property
    def clock(self) -> JWTClock:
        return self._clock

    @property
    def config(self) -> JWTConfig:
        return self._config

    def add_key(
        self,
        algorithm: Optional[str] = None,
        kid: Optional[str] = None,
        secret: Optional[bytes] = None,
        set_active: bool = True,
    ) -> SigningKey:
        alg = algorithm or self._config.default_algorithm
        if alg not in self._config.allowed_algorithms:
            raise ValueError(f"Algorithm '{alg}' not in allowed algorithms")

        now = self._clock.now()
        key = SigningKey(
            kid=kid or _generate_kid(),
            secret=secret or _generate_secret(),
            algorithm=alg,
            created_at=now,
            retire_at=now + self._config.key_retire_seconds,
            is_active=set_active,
        )

        with self._lock:
            if set_active and self._active_kid is not None:
                old_active = self._keys.get(self._active_kid)
                if old_active is not None:
                    self._keys[self._active_kid] = SigningKey(
                        kid=old_active.kid,
                        secret=old_active.secret,
                        algorithm=old_active.algorithm,
                        created_at=old_active.created_at,
                        retire_at=old_active.retire_at,
                        is_active=False,
                    )
                self._active_kid = key.kid
            elif set_active and self._active_kid is None:
                self._active_kid = key.kid

            self._keys[key.kid] = key
            self._cleanup_expired_locked()

        return key

    def rotate_key(
        self,
        algorithm: Optional[str] = None,
        kid: Optional[str] = None,
        secret: Optional[bytes] = None,
    ) -> SigningKey:
        return self.add_key(
            algorithm=algorithm,
            kid=kid,
            secret=secret,
            set_active=True,
        )

    def get_key(self, kid: str) -> SigningKey:
        with self._lock:
            self._cleanup_expired_locked()
            key = self._keys.get(kid)
            if key is None:
                raise KeyNotFoundError(kid)
            return key

    def get_active_key(self) -> SigningKey:
        with self._lock:
            self._cleanup_expired_locked()
            if self._active_kid is None:
                raise EmptyKeyStoreError("No active signing key in key store")
            key = self._keys.get(self._active_kid)
            if key is None:
                raise EmptyKeyStoreError("Active signing key not found in key store")
            return key

    def has_key(self, kid: str) -> bool:
        with self._lock:
            self._cleanup_expired_locked()
            return kid in self._keys

    def remove_key(self, kid: str) -> None:
        with self._lock:
            self._keys.pop(kid, None)
            if self._active_kid == kid:
                self._active_kid = None

    def list_keys(self) -> list[SigningKey]:
        with self._lock:
            self._cleanup_expired_locked()
            return list(self._keys.values())

    def active_kid(self) -> Optional[str]:
        with self._lock:
            self._cleanup_expired_locked()
            return self._active_kid

    def cleanup_expired(self) -> int:
        with self._lock:
            return self._cleanup_expired_locked()

    def _cleanup_expired_locked(self) -> int:
        now = self._clock.now()
        expired: list[str] = [
            kid for kid, key in self._keys.items() if now >= key.retire_at
        ]
        for kid in expired:
            del self._keys[kid]
            if self._active_kid == kid:
                self._active_kid = None
        return len(expired)

    def __len__(self) -> int:
        with self._lock:
            self._cleanup_expired_locked()
            return len(self._keys)

    def __contains__(self, kid: str) -> bool:
        return self.has_key(kid)


__all__ = ["KeyStore"]
