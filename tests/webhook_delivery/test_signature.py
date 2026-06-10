from __future__ import annotations

import pytest

from solocoder_py.webhook_delivery import (
    SIGNATURE_VERSION,
    SignatureVerificationError,
    compute_signature,
    verify_signature,
)


class TestComputeSignature:
    def test_signature_has_correct_prefix(self):
        sig = compute_signature(
            payload={"key": "value"},
            signing_secret="secret",
            timestamp=1234567890.0,
        )
        assert sig.startswith(f"{SIGNATURE_VERSION}=")

    def test_signature_is_deterministic(self):
        sig1 = compute_signature(
            payload={"a": 1, "b": 2},
            signing_secret="secret",
            timestamp=1000.0,
        )
        sig2 = compute_signature(
            payload={"a": 1, "b": 2},
            signing_secret="secret",
            timestamp=1000.0,
        )
        assert sig1 == sig2

    def test_different_payloads_produce_different_signatures(self):
        sig1 = compute_signature(
            payload={"key": "value1"},
            signing_secret="secret",
            timestamp=1000.0,
        )
        sig2 = compute_signature(
            payload={"key": "value2"},
            signing_secret="secret",
            timestamp=1000.0,
        )
        assert sig1 != sig2

    def test_different_secrets_produce_different_signatures(self):
        sig1 = compute_signature(
            payload={"key": "value"},
            signing_secret="secret1",
            timestamp=1000.0,
        )
        sig2 = compute_signature(
            payload={"key": "value"},
            signing_secret="secret2",
            timestamp=1000.0,
        )
        assert sig1 != sig2

    def test_different_timestamps_produce_different_signatures(self):
        sig1 = compute_signature(
            payload={"key": "value"},
            signing_secret="secret",
            timestamp=1000.0,
        )
        sig2 = compute_signature(
            payload={"key": "value"},
            signing_secret="secret",
            timestamp=2000.0,
        )
        assert sig1 != sig2

    def test_payload_key_ordering_is_irrelevant(self):
        sig1 = compute_signature(
            payload={"a": 1, "b": 2},
            signing_secret="secret",
            timestamp=1000.0,
        )
        sig2 = compute_signature(
            payload={"b": 2, "a": 1},
            signing_secret="secret",
            timestamp=1000.0,
        )
        assert sig1 == sig2

    def test_empty_payload(self):
        sig = compute_signature(
            payload={},
            signing_secret="secret",
            timestamp=0.0,
        )
        assert sig.startswith(f"{SIGNATURE_VERSION}=")
        assert len(sig) > len(f"{SIGNATURE_VERSION}=")

    def test_complex_nested_payload(self):
        payload = {
            "order": {
                "id": "123",
                "items": [{"name": "a", "qty": 1}, {"name": "b", "qty": 2}],
                "total": 99.99,
                "tags": None,
            },
            "meta": {"ts": 12345},
        }
        sig1 = compute_signature(
            payload=payload,
            signing_secret="my-key",
            timestamp=1700000000.0,
        )
        sig2 = compute_signature(
            payload=payload,
            signing_secret="my-key",
            timestamp=1700000000.0,
        )
        assert sig1 == sig2

    def test_signature_length_sha256_hex(self):
        sig = compute_signature(
            payload={"x": 1},
            signing_secret="s",
            timestamp=0.0,
        )
        hex_part = sig.split("=", 1)[1]
        assert len(hex_part) == 64


class TestVerifySignature:
    def test_valid_signature_verifies(self):
        payload = {"order_id": "123"}
        secret = "top_secret"
        ts = 1700000000.0
        sig = compute_signature(payload, secret, ts)
        verify_signature(
            payload=payload,
            signing_secret=secret,
            timestamp=ts,
            signature=sig,
        )

    def test_tampered_signature_raises(self):
        payload = {"order_id": "123"}
        secret = "top_secret"
        ts = 1700000000.0
        sig = compute_signature(payload, secret, ts)
        tampered = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload=payload,
                signing_secret=secret,
                timestamp=ts,
                signature=tampered,
            )

    def test_wrong_secret_raises(self):
        payload = {"x": 1}
        sig = compute_signature(payload, "correct", 1000.0)
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload=payload,
                signing_secret="wrong",
                timestamp=1000.0,
                signature=sig,
            )

    def test_tampered_payload_raises(self):
        sig = compute_signature({"x": 1}, "secret", 1000.0)
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 2},
                signing_secret="secret",
                timestamp=1000.0,
                signature=sig,
            )

    def test_empty_signature_raises(self):
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 1},
                signing_secret="s",
                timestamp=0.0,
                signature="",
            )

    def test_signature_without_equals_raises(self):
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 1},
                signing_secret="s",
                timestamp=0.0,
                signature="v1abcdef",
            )

    def test_unsupported_version_raises(self):
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 1},
                signing_secret="s",
                timestamp=0.0,
                signature="v2=abc",
            )

    def test_timestamp_within_tolerance_passes(self):
        ts = 1000.0
        sig = compute_signature({"x": 1}, "secret", ts)
        verify_signature(
            payload={"x": 1},
            signing_secret="secret",
            timestamp=ts,
            signature=sig,
            tolerance_seconds=300,
            current_time=ts + 299,
        )

    def test_timestamp_outside_tolerance_raises(self):
        ts = 1000.0
        sig = compute_signature({"x": 1}, "secret", ts)
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 1},
                signing_secret="secret",
                timestamp=ts,
                signature=sig,
                tolerance_seconds=300,
                current_time=ts + 301,
            )

    def test_timestamp_in_past_outside_tolerance_raises(self):
        ts = 1000.0
        sig = compute_signature({"x": 1}, "secret", ts)
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 1},
                signing_secret="secret",
                timestamp=ts,
                signature=sig,
                tolerance_seconds=300,
                current_time=ts - 301,
            )

    def test_no_current_time_skips_timestamp_check(self):
        ts = 0.0
        sig = compute_signature({"x": 1}, "secret", ts)
        verify_signature(
            payload={"x": 1},
            signing_secret="secret",
            timestamp=ts,
            signature=sig,
            tolerance_seconds=1,
            current_time=None,
        )

    def test_very_large_timestamp_difference_raises(self):
        ts = 0.0
        sig = compute_signature({"x": 1}, "secret", ts)
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 1},
                signing_secret="secret",
                timestamp=ts,
                signature=sig,
                tolerance_seconds=5,
                current_time=1_000_000,
            )

    def test_boundary_zero_tolerance(self):
        ts = 1000.0
        sig = compute_signature({"x": 1}, "secret", ts)
        verify_signature(
            payload={"x": 1},
            signing_secret="secret",
            timestamp=ts,
            signature=sig,
            tolerance_seconds=0,
            current_time=ts,
        )

    def test_boundary_exact_tolerance(self):
        ts = 1000.0
        sig = compute_signature({"x": 1}, "secret", ts)
        verify_signature(
            payload={"x": 1},
            signing_secret="secret",
            timestamp=ts,
            signature=sig,
            tolerance_seconds=10,
            current_time=ts + 10,
        )

    def test_payload_tamper_add_key_raises(self):
        original = {"a": 1}
        sig = compute_signature(original, "secret", 1000.0)
        tampered = {"a": 1, "b": 2}
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload=tampered,
                signing_secret="secret",
                timestamp=1000.0,
                signature=sig,
            )

    def test_payload_tamper_remove_key_raises(self):
        original = {"a": 1, "b": 2}
        sig = compute_signature(original, "secret", 1000.0)
        tampered = {"a": 1}
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload=tampered,
                signing_secret="secret",
                timestamp=1000.0,
                signature=sig,
            )

    def test_payload_tamper_change_value_type_raises(self):
        original = {"amount": 100}
        sig = compute_signature(original, "secret", 1000.0)
        tampered = {"amount": "100"}
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload=tampered,
                signing_secret="secret",
                timestamp=1000.0,
                signature=sig,
            )

    def test_payload_tamper_nested_value_raises(self):
        original = {"order": {"id": "123", "total": 99.99}}
        sig = compute_signature(original, "secret", 1000.0)
        tampered = {"order": {"id": "123", "total": 199.99}}
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload=tampered,
                signing_secret="secret",
                timestamp=1000.0,
                signature=sig,
            )

    def test_payload_tamper_empty_to_nonempty_raises(self):
        sig = compute_signature({}, "secret", 1000.0)
        with pytest.raises(SignatureVerificationError):
            verify_signature(
                payload={"x": 1},
                signing_secret="secret",
                timestamp=1000.0,
                signature=sig,
            )

    def test_payload_valid_identical_content_passes(self):
        payload = {"b": 2, "a": 1, "nested": {"z": 26, "a": 1}}
        sig = compute_signature(payload, "secret", 1000.0)
        verify_signature(
            payload=payload,
            signing_secret="secret",
            timestamp=1000.0,
            signature=sig,
        )
