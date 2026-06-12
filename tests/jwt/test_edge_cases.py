from __future__ import annotations

import json
import base64

import pytest

from solocoder_py.jwt import (
    EmptyKeyStoreError,
    ExpiredTokenError,
    ImmatureTokenError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidIssuerError,
    JWTConfig,
    JWTService,
    KeyNotFoundError,
    KeyStore,
    SignOptions,
    compute_signature,
    b64url_encode,
)
from solocoder_py.seat.clock import ManualClock
from solocoder_py.jwt import JWTClock


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class TestNbfNotBefore:
    def test_nbf_in_past_allowed(self, jwt_service: JWTService, manual_clock: ManualClock, base_timestamp):
        past_nbf = base_timestamp - 100
        token = jwt_service.encode(
            {"sub": "nbf-past", "nbf": past_nbf}, SignOptions(expire_seconds=1000)
        )
        verified = jwt_service.decode(token)
        assert verified["nbf"] == past_nbf

    def test_nbf_in_future_rejected(self, jwt_service: JWTService, manual_clock: ManualClock, base_timestamp):
        future_nbf = base_timestamp + 100
        token = jwt_service.encode(
            {"sub": "nbf-future", "nbf": future_nbf},
            SignOptions(expire_seconds=1000),
        )
        with pytest.raises(ImmatureTokenError):
            jwt_service.decode(token)

    def test_nbf_in_future_then_passes_after_time(self, jwt_service: JWTService, manual_clock: ManualClock, base_timestamp):
        future_nbf = base_timestamp + 100
        token = jwt_service.encode(
            {"sub": "nbf-wait", "nbf": future_nbf},
            SignOptions(expire_seconds=1000)
        )

        with pytest.raises(ImmatureTokenError):
            jwt_service.decode(token)

        manual_clock.advance(100)

        verified = jwt_service.decode(token)
        assert verified["sub"] == "nbf-wait"

    def test_nbf_equal_now_boundary(self, jwt_service: JWTService, manual_clock: ManualClock, base_timestamp):
        token = jwt_service.encode(
            {"sub": "nbf-boundary", "nbf": base_timestamp},
            SignOptions(expire_seconds=1000)
        )
        verified = jwt_service.decode(token)
        assert verified["nbf"] == base_timestamp


class TestTimeBoundaries:
    def test_exp_at_exact_moment_rejected(self, jwt_service: JWTService, manual_clock: ManualClock, base_timestamp):
        expire_seconds = 100
        token = jwt_service.encode(
            {"sub": "exp-boundary"}, SignOptions(expire_seconds=expire_seconds)
        )

        manual_clock.advance(expire_seconds)
        with pytest.raises(ExpiredTokenError):
            jwt_service.decode(token)

    def test_exp_one_second_before_expiry_valid(
        self, jwt_service: JWTService, manual_clock: ManualClock):
        token = jwt_service.encode(
            {"sub": "exp-almost"}, SignOptions(expire_seconds=100)
        )

        manual_clock.advance(99)
        verified = jwt_service.decode(token)
        assert verified["sub"] == "exp-almost"


class TestAudienceArray:
    def test_aud_array_with_multiple_values_hit_first(self, default_config, jwt_clock):
        default_config.audiences = ["svc-a", "svc-b", "svc-c"]
        default_config.current_service_id = "svc-a"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="aud-arr-k1")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "aud-multi"})
        verified = service.decode(token)
        assert verified["aud"] == ["svc-a", "svc-b", "svc-c"]

    def test_aud_array_with_multiple_values_hit_middle(self, default_config, jwt_clock):
        default_config.audiences = ["svc-a", "svc-b", "svc-c"]
        default_config.current_service_id = "svc-b"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="aud-arr-k2")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "aud-multi-mid"})
        verified = service.decode(token)
        assert verified["aud"] == ["svc-a", "svc-b", "svc-c"]

    def test_aud_array_with_multiple_values_hit_last(self, default_config, jwt_clock):
        default_config.audiences = ["svc-a", "svc-b", "svc-c"]
        default_config.current_service_id = "svc-c"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="aud-arr-k3")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "aud-multi-last"})
        verified = service.decode(token)
        assert verified["aud"] == ["svc-a", "svc-b", "svc-c"]

    def test_aud_array_none_match_rejected(self, default_config, jwt_clock):
        default_config.audiences = ["svc-a", "svc-b"]
        default_config.current_service_id = "svc-z"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="aud-arr-k4")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "aud-miss"})
        with pytest.raises(InvalidAudienceError):
            service.decode(token)

    def test_aud_string_single_value_match(self, default_config, jwt_clock):
        default_config.audiences = ["single-svc"]
        default_config.current_service_id = "single-svc"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="aud-str-k1")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "aud-str"})
        verified = service.decode(token)
        assert verified["aud"] == ["single-svc"]


class TestKidNotFound:
    def test_kid_not_in_store(self, jwt_service: JWTService):
        token = jwt_service.encode({"sub": "kid-test"})
        parts = token.split(".")
        header_bytes = _b64url_decode(parts[0])
        header = json.loads(header_bytes)
        header["kid"] = "non-existent-kid"
        new_header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True).encode()
        ).decode()
        payload_b64 = parts[1]
        signing_input = f"{new_header_b64}.{payload_b64}".encode("ascii")
        original_key = jwt_service.key_store.get_key("key-v1")
        signature = compute_signature("HS256", original_key.secret, signing_input)
        sig_b64 = b64url_encode(signature).decode()

        tampered = f"{new_header_b64}.{payload_b64}.{sig_b64}"

        with pytest.raises(KeyNotFoundError):
            jwt_service.decode(tampered)


class TestEmptyKeyStore:
    def test_encode_with_empty_store(self, default_config, jwt_clock):
        ks = KeyStore(default_config, jwt_clock)
        service = JWTService(default_config, ks, jwt_clock)

        with pytest.raises(EmptyKeyStoreError):
            service.encode({"sub": "empty-store"})

    def test_get_active_key_empty(self, default_config, jwt_clock):
        ks = KeyStore(default_config, jwt_clock)
        with pytest.raises(EmptyKeyStoreError):
            ks.get_active_key()

    def test_remove_then_encode_fails(self, jwt_service: JWTService):
        jwt_service.key_store.remove_key("key-v1")
        with pytest.raises(EmptyKeyStoreError):
            jwt_service.encode({"sub": "after-remove"})
