from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any, Optional

from .exceptions import (
    ExpiredTokenError,
    ImmatureTokenError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    JWTError,
    MalformedTokenError,
    MissingClaimError,
)
from .models import (
    DecodedJWT,
    JWTClock,
    JWTConfig,
    SignOptions,
    VerifiedJWT,
)
from .store import KeyStore


_HMAC_HASH_MAP: dict[str, Any] = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}


def b64url_encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def b64url_decode(data: str | bytes) -> bytes:
    if isinstance(data, str):
        data = data.encode("ascii")
    padding = b"=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def compute_signature(algorithm: str, key: bytes, signing_input: bytes) -> bytes:
    hash_func = _HMAC_HASH_MAP.get(algorithm)
    if hash_func is None:
        raise InvalidAlgorithmError(f"Unsupported algorithm: {algorithm}")
    return hmac.new(key, signing_input, hash_func).digest()


def constant_time_compare(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)


def parse_jwt(token: str) -> DecodedJWT:
    if not isinstance(token, str):
        raise MalformedTokenError("Token must be a string")

    parts = token.split(".")
    if len(parts) != 3:
        raise MalformedTokenError(
            f"JWT token must have 3 parts separated by '.', got {len(parts)}"
        )

    header_b64, payload_b64, signature_b64 = parts

    try:
        header_bytes = b64url_decode(header_b64)
    except Exception as exc:
        raise MalformedTokenError(f"Failed to decode header: {exc}") from exc

    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MalformedTokenError(f"Header is not valid JSON: {exc}") from exc

    if not isinstance(header, dict):
        raise MalformedTokenError("Header must be a JSON object")

    try:
        payload_bytes = b64url_decode(payload_b64)
    except Exception as exc:
        raise MalformedTokenError(f"Failed to decode payload: {exc}") from exc

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MalformedTokenError(f"Payload is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise MalformedTokenError("Payload must be a JSON object")

    try:
        signature = b64url_decode(signature_b64)
    except Exception as exc:
        raise MalformedTokenError(f"Failed to decode signature: {exc}") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    return DecodedJWT(
        header=header,
        payload=payload,
        signature=signature,
        signing_input=signing_input,
    )


class JWTService:
    def __init__(
        self,
        config: JWTConfig,
        key_store: Optional[KeyStore] = None,
        clock: Optional[JWTClock] = None,
    ) -> None:
        self._config: JWTConfig = config
        self._clock: JWTClock = clock or JWTClock()
        self._key_store: KeyStore = key_store or KeyStore(config, self._clock)

    @property
    def config(self) -> JWTConfig:
        return self._config

    @property
    def key_store(self) -> KeyStore:
        return self._key_store

    @property
    def clock(self) -> JWTClock:
        return self._clock

    def encode(
        self,
        claims: dict[str, Any],
        options: Optional[SignOptions] = None,
    ) -> str:
        opts = options or SignOptions()
        algorithm = opts.algorithm or self._config.default_algorithm

        if algorithm not in self._config.allowed_algorithms:
            raise InvalidAlgorithmError(
                f"Algorithm '{algorithm}' not in allowed whitelist: {self._config.allowed_algorithms}"
            )

        active_key = self._key_store.get_active_key()

        if active_key.algorithm != algorithm:
            raise InvalidAlgorithmError(
                f"Active key uses algorithm '{active_key.algorithm}', "
                f"but requested algorithm is '{algorithm}'"
            )

        now = self._clock.now()

        payload: dict[str, Any] = dict(claims)

        payload["iss"] = self._config.issuer

        if self._config.audiences:
            payload["aud"] = list(self._config.audiences)

        expire_seconds = (
            opts.expire_seconds
            if opts.expire_seconds is not None
            else self._config.default_expire_seconds
        )
        if expire_seconds > 0:
            payload["exp"] = now + expire_seconds

        if opts.include_iat:
            payload["iat"] = now

        if opts.include_jti and "jti" not in payload:
            payload["jti"] = secrets.token_urlsafe(16)

        header: dict[str, Any] = {
            "typ": "JWT",
            "alg": algorithm,
            "kid": active_key.kid,
        }
        header.update(opts.extra_headers)

        header_bytes = json.dumps(
            header, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        payload_bytes = json.dumps(
            payload, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")

        header_b64 = b64url_encode(header_bytes).decode("ascii")
        payload_b64 = b64url_encode(payload_bytes).decode("ascii")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

        signature = compute_signature(algorithm, active_key.secret, signing_input)
        signature_b64 = b64url_encode(signature).decode("ascii")

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def decode(
        self,
        token: str,
    ) -> VerifiedJWT:
        decoded = parse_jwt(token)

        header_alg = decoded.header.get("alg")
        if header_alg is None:
            raise InvalidAlgorithmError("JWT header missing 'alg' field")
        if not isinstance(header_alg, str):
            raise InvalidAlgorithmError(
                f"JWT header 'alg' must be a string, got {type(header_alg).__name__}"
            )
        if header_alg not in self._config.allowed_algorithms:
            raise InvalidAlgorithmError(
                f"Algorithm '{header_alg}' not in allowed whitelist: {self._config.allowed_algorithms}"
            )

        kid = decoded.header.get("kid")
        if kid is None:
            raise JWTError("JWT header missing 'kid' field")
        if not isinstance(kid, str):
            raise JWTError(
                f"JWT header 'kid' must be a string, got {type(kid).__name__}"
            )

        signing_key = self._key_store.get_key(kid)

        if signing_key.algorithm != header_alg:
            raise InvalidAlgorithmError(
                f"Key algorithm mismatch: key uses '{signing_key.algorithm}', "
                f"JWT header specifies '{header_alg}'"
            )

        expected_signature = compute_signature(
            header_alg, signing_key.secret, decoded.signing_input
        )
        if not constant_time_compare(expected_signature, decoded.signature):
            raise InvalidSignatureError("JWT signature verification failed")

        now = self._clock.now()
        payload = decoded.payload

        self._verify_iss(payload)
        self._verify_aud(payload)
        self._verify_exp(payload, now)
        self._verify_nbf(payload, now)

        return VerifiedJWT(header=decoded.header, payload=payload)

    def _verify_iss(self, payload: dict[str, Any]) -> None:
        if "iss" not in payload:
            raise MissingClaimError("iss")
        iss = payload["iss"]
        if not isinstance(iss, str):
            raise InvalidIssuerError(str(iss), self._config.allowed_issuers)
        if iss not in self._config.allowed_issuers:
            raise InvalidIssuerError(iss, list(self._config.allowed_issuers))

    def _verify_aud(self, payload: dict[str, Any]) -> None:
        if "aud" not in payload:
            raise MissingClaimError("aud")
        aud = payload["aud"]

        expected = self._config.current_service_id
        if expected is None and self._config.audiences:
            expected = self._config.audiences[0]
        if expected is None:
            raise JWTError("Cannot verify aud: no current_service_id or audiences configured")

        if isinstance(aud, str):
            aud_list = [aud]
        elif isinstance(aud, list):
            aud_list = list(aud)
            for item in aud_list:
                if not isinstance(item, str):
                    raise InvalidAudienceError(aud, expected)
        else:
            raise InvalidAudienceError(aud, expected)

        if expected not in aud_list:
            raise InvalidAudienceError(aud, expected)

    def _verify_exp(self, payload: dict[str, Any], now: float) -> None:
        if "exp" not in payload:
            raise MissingClaimError("exp")
        exp = payload["exp"]
        if not isinstance(exp, (int, float)):
            raise ExpiredTokenError(float("inf"), now)
        if now >= float(exp):
            raise ExpiredTokenError(float(exp), now)

    def _verify_nbf(self, payload: dict[str, Any], now: float) -> None:
        if "nbf" not in payload:
            return
        nbf = payload["nbf"]
        if not isinstance(nbf, (int, float)):
            raise ImmatureTokenError(float("inf"), now)
        if now < float(nbf):
            raise ImmatureTokenError(float(nbf), now)

    def rotate_key(
        self,
        algorithm: Optional[str] = None,
        kid: Optional[str] = None,
        secret: Optional[bytes] = None,
    ) -> Any:
        return self._key_store.rotate_key(
            algorithm=algorithm,
            kid=kid,
            secret=secret,
        )


__all__ = [
    "b64url_encode",
    "b64url_decode",
    "compute_signature",
    "constant_time_compare",
    "parse_jwt",
    "JWTService",
]
