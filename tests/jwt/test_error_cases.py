from __future__ import annotations

import json
import base64

import pytest

from solocoder_py.jwt import (
    ExpiredTokenError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    JWTConfig,
    JWTError,
    JWTService,
    KeyNotFoundError,
    KeyStore,
    MalformedTokenError,
    MissingClaimError,
    SignOptions,
    b64url_encode,
    b64url_decode,
    compute_signature,
    parse_jwt,
)
from solocoder_py.seat.clock import ManualClock
from solocoder_py.jwt import JWTClock


class TestNoneAlgorithmRejected:
    def test_none_alg_in_header_rejected(self, jwt_service: JWTService):
        token = jwt_service.encode({"sub": "none-test"})
        parts = token.split(".")

        header_bytes = b64url_decode(parts[0])
        header = json.loads(header_bytes)
        header["alg"] = "none"
        new_header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True).encode()
        ).decode()

        malformed = f"{new_header_b64}.{parts[1]}.{parts[2]}"

        with pytest.raises(InvalidAlgorithmError):
            jwt_service.decode(malformed)

    def test_none_alg_empty_sig_rejected(self, jwt_service: JWTService):
        header = {"alg": "none", "typ": "JWT", "kid": "key-v1"}
        payload = {
            "sub": "attacker",
            "iss": jwt_service.config.issuer,
            "aud": ["service-a"],
            "exp": 1e18,
        }
        header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True).encode()
        ).decode()
        payload_b64 = b64url_encode(
            json.dumps(payload, sort_keys=True).encode()
        ).decode()

        fake_token = f"{header_b64}.{payload_b64}."

        with pytest.raises(InvalidAlgorithmError):
            jwt_service.decode(fake_token)


class TestRemovedKeySigningFails:
    def test_verify_token_signed_with_removed_key_fails(
        self, default_config, jwt_clock
    ):
        ks = KeyStore(default_config, jwt_clock)
        key1 = ks.add_key(algorithm="HS256", kid="ephemeral-key")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "signed-with-old"})
        assert service.decode(token)["sub"] == "signed-with-old"

        ks.remove_key("ephemeral-key")

        with pytest.raises(KeyNotFoundError):
            service.decode(token)

    def test_old_key_retired_after_cleanup(self, default_config, manual_clock):
        short_retire_config = JWTConfig(
            issuer=default_config.issuer,
            audiences=default_config.audiences,
            allowed_algorithms=default_config.allowed_algorithms,
            default_algorithm=default_config.default_algorithm,
            default_expire_seconds=3600,
            key_retire_seconds=10,
            current_service_id=default_config.current_service_id,
            allowed_issuers=default_config.allowed_issuers,
        )
        jwt_clock = JWTClock.from_clock(manual_clock)
        ks = KeyStore(short_retire_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="temp-key")
        service = JWTService(short_retire_config, ks, jwt_clock)

        token = service.encode({"sub": "retire-me"})
        assert service.decode(token)["sub"] == "retire-me"

        manual_clock.advance(10)

        assert len(ks.list_keys()) == 0
        with pytest.raises(KeyNotFoundError):
            service.decode(token)


class TestTamperedSignature:
    def test_signature_bytes_modified(self, jwt_service: JWTService):
        token = jwt_service.encode({"sub": "tamper-test"})
        parts = token.split(".")

        sig_bytes = bytearray(b64url_decode(parts[2]))
        sig_bytes[0] ^= 0xFF
        new_sig_b64 = b64url_encode(bytes(sig_bytes)).decode()

        tampered = f"{parts[0]}.{parts[1]}.{new_sig_b64}"

        with pytest.raises(InvalidSignatureError):
            jwt_service.decode(tampered)

    def test_payload_modified_signature_invalid(self, jwt_service: JWTService):
        token = jwt_service.encode({"sub": "original", "role": "user"})
        parts = token.split(".")

        payload_bytes = b64url_decode(parts[1])
        payload = json.loads(payload_bytes)
        payload["role"] = "admin"
        new_payload_b64 = b64url_encode(
            json.dumps(payload, sort_keys=True).encode()
        ).decode()

        tampered = f"{parts[0]}.{new_payload_b64}.{parts[2]}"

        with pytest.raises(InvalidSignatureError):
            jwt_service.decode(tampered)

    def test_header_modified_breaks_signature(self, jwt_service: JWTService):
        token = jwt_service.encode({"sub": "header-tamper"})
        parts = token.split(".")

        header_bytes = b64url_decode(parts[0])
        header = json.loads(header_bytes)
        header["extra"] = "malicious"
        new_header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True).encode()
        ).decode()

        tampered = f"{new_header_b64}.{parts[1]}.{parts[2]}"

        with pytest.raises(InvalidSignatureError):
            jwt_service.decode(tampered)


class TestMalformedJWT:
    def test_missing_two_dots_single_part(self, jwt_service: JWTService):
        with pytest.raises(MalformedTokenError):
            jwt_service.decode("singlepartstring")

    def test_missing_one_dot_two_parts(self, jwt_service: JWTService):
        with pytest.raises(MalformedTokenError):
            jwt_service.decode("header.payload")

    def test_four_parts_extra_dot(self, jwt_service: JWTService):
        with pytest.raises(MalformedTokenError):
            jwt_service.decode("a.b.c.d")

    def test_empty_string(self, jwt_service: JWTService):
        with pytest.raises(MalformedTokenError):
            jwt_service.decode("")

    def test_header_not_valid_base64(self, jwt_service: JWTService):
        with pytest.raises(MalformedTokenError):
            jwt_service.decode("!!!not-base64!!!.eyJhIjoiYiJ9.c2ln")

    def test_header_not_json(self, jwt_service: JWTService):
        not_json_b64 = b64url_encode(b"this is not json").decode()
        token = f"{not_json_b64}.eyJhIjoiYiJ9.c2ln"
        with pytest.raises(MalformedTokenError):
            parse_jwt(token)

    def test_payload_not_valid_base64(self, jwt_service: JWTService):
        header_b64 = b64url_encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).decode()
        with pytest.raises(MalformedTokenError):
            parse_jwt(f"{header_b64}.!!!bad-base64!!!.c2ln")

    def test_payload_not_json(self, jwt_service: JWTService):
        header_b64 = b64url_encode(
            json.dumps({"alg": "HS256", "typ": "JWT", "kid": "key-v1"}, sort_keys=True).encode()
        ).decode()
        not_json_b64 = b64url_encode(b"definitely not json here").decode()
        key = jwt_service.key_store.get_active_key()
        signing_input = f"{header_b64}.{not_json_b64}".encode()
        sig = compute_signature("HS256", key.secret, signing_input)
        sig_b64 = b64url_encode(sig).decode()
        token = f"{header_b64}.{not_json_b64}.{sig_b64}"
        with pytest.raises(MalformedTokenError):
            parse_jwt(token)

    def test_header_is_array_not_object(self, jwt_service: JWTService):
        header_b64 = b64url_encode(json.dumps(["not", "an", "object"]).encode()).decode()
        with pytest.raises(MalformedTokenError):
            parse_jwt(f"{header_b64}.eyJhIjoiYiJ9.c2ln")

    def test_payload_is_array_not_object(self, jwt_service: JWTService):
        payload_b64 = b64url_encode(json.dumps([1, 2, 3]).encode()).decode()
        header_b64 = b64url_encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}, sort_keys=True).encode()
        ).decode()
        with pytest.raises(MalformedTokenError):
            parse_jwt(f"{header_b64}.{payload_b64}.c2ln")


class TestExpiredCannotBeBypassed:
    def test_expired_with_valid_aud_iss_still_rejected(
        self, jwt_service: JWTService, manual_clock: ManualClock
    ):
        token = jwt_service.encode(
            {"sub": "exp-bypass", "aud": ["service-a"]},
            SignOptions(expire_seconds=50)
        )
        manual_clock.advance(100)

        with pytest.raises(ExpiredTokenError):
            jwt_service.decode(token)

    def test_expired_with_correct_nbf_still_rejected(
        self, jwt_service: JWTService, manual_clock: ManualClock, base_timestamp
    ):
        token = jwt_service.encode(
            {
                "sub": "exp-and-nbf",
                "nbf": base_timestamp - 1000,
            },
            SignOptions(expire_seconds=50),
        )
        manual_clock.advance(100)

        with pytest.raises(ExpiredTokenError):
            jwt_service.decode(token)

    def test_valid_exp_but_invalid_iss_still_rejected(self, default_config, jwt_clock):
        default_config.allowed_issuers = ["only-this-issuer"]
        default_config.issuer = "malicious-issuer"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="iss-k")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "wrong-iss"}, SignOptions(expire_seconds=1000))

        with pytest.raises(InvalidIssuerError):
            service.decode(token)

    def test_valid_exp_but_invalid_aud_still_rejected(self, default_config, jwt_clock):
        default_config.audiences = ["correct-audience"]
        default_config.current_service_id = "wrong-service"
        ks = KeyStore(default_config, jwt_clock)
        ks.add_key(algorithm="HS256", kid="aud-k")
        service = JWTService(default_config, ks, jwt_clock)

        token = service.encode({"sub": "wrong-aud"}, SignOptions(expire_seconds=1000))

        with pytest.raises(InvalidAudienceError):
            service.decode(token)


class TestMissingRequiredClaims:
    def test_missing_iss_claim_rejected(self, jwt_service: JWTService, manual_clock: ManualClock):
        key = jwt_service.key_store.get_active_key()
        now = jwt_service.clock.now()
        payload = {
            "sub": "no-iss",
            "aud": ["service-a"],
            "exp": now + 3600,
        }
        header = {"alg": key.algorithm, "typ": "JWT", "kid": key.kid}
        header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True).encode()
        ).decode()
        payload_b64 = b64url_encode(
            json.dumps(payload, sort_keys=True).encode()
        ).decode()
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = compute_signature(key.algorithm, key.secret, signing_input)
        sig_b64 = b64url_encode(sig).decode()
        token = f"{header_b64}.{payload_b64}.{sig_b64}"

        with pytest.raises(MissingClaimError):
            jwt_service.decode(token)

    def test_missing_aud_claim_rejected(self, jwt_service: JWTService):
        key = jwt_service.key_store.get_active_key()
        now = jwt_service.clock.now()
        payload = {
            "sub": "no-aud",
            "iss": jwt_service.config.issuer,
            "exp": now + 3600,
        }
        header = {"alg": key.algorithm, "typ": "JWT", "kid": key.kid}
        header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True).encode()
        ).decode()
        payload_b64 = b64url_encode(
            json.dumps(payload, sort_keys=True).encode()
        ).decode()
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = compute_signature(key.algorithm, key.secret, signing_input)
        sig_b64 = b64url_encode(sig).decode()
        token = f"{header_b64}.{payload_b64}.{sig_b64}"

        with pytest.raises(MissingClaimError):
            jwt_service.decode(token)

    def test_missing_exp_claim_rejected(self, jwt_service: JWTService):
        key = jwt_service.key_store.get_active_key()
        payload = {
            "sub": "no-exp",
            "iss": jwt_service.config.issuer,
            "aud": ["service-a"],
        }
        header = {"alg": key.algorithm, "typ": "JWT", "kid": key.kid}
        header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True).encode()
        ).decode()
        payload_b64 = b64url_encode(
            json.dumps(payload, sort_keys=True).encode()
        ).decode()
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = compute_signature(key.algorithm, key.secret, signing_input)
        sig_b64 = b64url_encode(sig).decode()
        token = f"{header_b64}.{payload_b64}.{sig_b64}"

        with pytest.raises(MissingClaimError):
            jwt_service.decode(token)
