from __future__ import annotations

import json
import base64

import pytest

from solocoder_py.jwt import (
    ExpiredTokenError,
    InvalidAlgorithmError,
    JWTConfig,
    JWTService,
    KeyStore,
    SignOptions,
)
from solocoder_py.seat.clock import ManualClock
from solocoder_py.jwt import JWTClock


def _b64url_encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class TestHMACSignAndVerify:
    def test_hs256_sign_and_verify_success(self, jwt_service: JWTService, base_timestamp: float):
        claims = {"sub": "user-123", "role": "admin", "custom": "value"}
        token = jwt_service.encode(claims)
        verified = jwt_service.decode(token)

        assert verified["sub"] == "user-123"
        assert verified["role"] == "admin"
        assert verified["custom"] == "value"
        assert verified["iss"] == jwt_service.config.issuer
        assert verified["aud"] == ["service-a", "service-b"]
        assert "exp" in verified
        assert "iat" in verified
        assert "jti" in verified
        assert verified.header["alg"] == "HS256"
        assert verified.header["kid"] == "key-v1"

    def test_hs384_sign_and_verify_success(self, default_config, jwt_clock):
        default_config.default_algorithm = "HS384"
        default_config.allowed_algorithms = {"HS384"}
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS384", kid="key-hs384")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "user-hs384"}, SignOptions(algorithm="HS384"))
        verified = service.decode(token)

        assert verified["sub"] == "user-hs384"
        assert verified.header["alg"] == "HS384"

    def test_hs512_sign_and_verify_success(self, default_config, jwt_clock):
        default_config.default_algorithm = "HS512"
        default_config.allowed_algorithms = {"HS512"}
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS512", kid="key-hs512")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "user-hs512"}, SignOptions(algorithm="HS512"))
        verified = service.decode(token)

        assert verified["sub"] == "user-hs512"
        assert verified.header["alg"] == "HS512"

    def test_claims_round_trip_preserved(self, jwt_service: JWTService):
        claims = {
            "string": "hello",
            "int": 42,
            "bool": True,
            "null_val": None,
            "list": [1, 2, 3],
            "nested": {"a": 1},
        }
        token = jwt_service.encode(claims)
        verified = jwt_service.decode(token)

        assert verified["string"] == "hello"
        assert verified["int"] == 42
        assert verified["bool"] is True
        assert verified["null_val"] is None
        assert verified["list"] == [1, 2, 3]
        assert verified["nested"] == {"a": 1}


class TestKeyRotation:
    def test_rotate_key_new_token_uses_new_key(self, jwt_service: JWTService):
        old_active = jwt_service.key_store.get_active_key()
        assert old_active.kid == "key-v1"

        new_key = jwt_service.rotate_key(kid="key-v2")
        assert new_key.kid == "key-v2"
        assert jwt_service.key_store.active_kid() == "key-v2"

        token = jwt_service.encode({"sub": "user-new"})
        verified = jwt_service.decode(token)
        assert verified.header["kid"] == "key-v2"

    def test_rotate_key_old_token_still_valid(
        self, jwt_service: JWTService, manual_clock: ManualClock
    ):
        old_token = jwt_service.encode({"sub": "user-old"})

        jwt_service.rotate_key(kid="key-v2")

        verified_old = jwt_service.decode(old_token)
        assert verified_old["sub"] == "user-old"
        assert verified_old.header["kid"] == "key-v1"

        new_token = jwt_service.encode({"sub": "user-new"})
        verified_new = jwt_service.decode(new_token)
        assert verified_new["sub"] == "user-new"
        assert verified_new.header["kid"] == "key-v2"

    def test_rotate_multiple_keys_all_valid(self, jwt_service: JWTService):
        t1 = jwt_service.encode({"sub": "v1"})

        jwt_service.rotate_key(kid="key-v2")
        t2 = jwt_service.encode({"sub": "v2"})

        jwt_service.rotate_key(kid="key-v3")
        t3 = jwt_service.encode({"sub": "v3"})

        assert jwt_service.decode(t1)["sub"] == "v1"
        assert jwt_service.decode(t2)["sub"] == "v2"
        assert jwt_service.decode(t3)["sub"] == "v3"
        assert len(jwt_service.key_store.list_keys()) == 3


class TestAlgorithmWhitelist:
    def test_whitelist_algorithm_allowed_sign(self, default_config, jwt_clock):
        default_config.allowed_algorithms = {"HS256"}
        default_config.default_algorithm = "HS256"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="only-hs256")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "algo-test"}, SignOptions(algorithm="HS256"))
        verified = service.decode(token)
        assert verified.header["alg"] == "HS256"

    def test_whitelist_algorithm_not_allowed_sign(self, default_config, jwt_clock):
        default_config.allowed_algorithms = {"HS256"}
        default_config.default_algorithm = "HS256"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="only-hs256")
        service = JWTService(default_config, ks, jwt_clock)

        with pytest.raises(InvalidAlgorithmError):
            service.encode({"sub": "algo-test"}, SignOptions(algorithm="HS384"))

    def test_whitelist_algorithm_not_allowed_verify(self, jwt_service: JWTService):
        token = jwt_service.encode({"sub": "algo-test"})
        parts = token.split(".")

        header_bytes = _b64url_decode(parts[0])
        header = json.loads(header_bytes)
        header["alg"] = "none"
        new_header_b64 = _b64url_encode(json.dumps(header, sort_keys=True).encode()).decode()

        malformed = f"{new_header_b64}.{parts[1]}.{parts[2]}"

        with pytest.raises(InvalidAlgorithmError):
            jwt_service.decode(malformed)


class TestAudIssValidation:
    def test_aud_single_audience_hit(self, default_config, jwt_clock):
        default_config.audiences = ["target-service"]
        default_config.current_service_id = "target-service"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="aud-k1")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "aud-test"})
        verified = service.decode(token)
        assert verified["aud"] == ["target-service"]

    def test_iss_valid_issuer(self, default_config, jwt_clock):
        default_config.allowed_issuers = ["test-issuer", "issuer-b"]
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="iss-k1")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "iss-test"})
        verified = service.decode(token)
        assert verified["iss"] == "test-issuer"


class TestExpiration:
    def test_exp_before_expiry_valid(self, jwt_service: JWTService, manual_clock: ManualClock, base_timestamp):
        token = jwt_service.encode({"sub": "exp-test"}, SignOptions(expire_seconds=100))

        manual_clock.advance(50)
        verified = jwt_service.decode(token)
        assert verified["exp"] == base_timestamp + 100

    def test_exp_past_expiry_rejected(self, jwt_service: JWTService, manual_clock: ManualClock):
        token = jwt_service.encode({"sub": "exp-test"}, SignOptions(expire_seconds=100))

        manual_clock.advance(200)
        with pytest.raises(ExpiredTokenError):
            jwt_service.decode(token)
