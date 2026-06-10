from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping

from .exceptions import SignatureVerificationError


SIGNATURE_VERSION = "v1"


def _canonicalize_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_signature(
    payload: Mapping[str, Any],
    signing_secret: str,
    timestamp: float,
) -> str:
    payload_bytes = _canonicalize_payload(payload)
    timestamp_bytes = str(int(timestamp)).encode("utf-8")
    secret_bytes = signing_secret.encode("utf-8")

    mac = hmac.new(secret_bytes, digestmod=hashlib.sha256)
    mac.update(timestamp_bytes)
    mac.update(b".")
    mac.update(payload_bytes)

    return f"{SIGNATURE_VERSION}={mac.hexdigest()}"


def verify_signature(
    payload: Mapping[str, Any],
    signing_secret: str,
    timestamp: float,
    signature: str,
    tolerance_seconds: float = 300.0,
    current_time: float | None = None,
) -> None:
    if not signature or "=" not in signature:
        raise SignatureVerificationError("Invalid signature format")

    version, _, hex_digest = signature.partition("=")
    if version != SIGNATURE_VERSION:
        raise SignatureVerificationError(
            f"Unsupported signature version: {version}"
        )

    if current_time is not None:
        if abs(current_time - timestamp) > tolerance_seconds:
            raise SignatureVerificationError(
                f"Timestamp outside tolerance window: {abs(current_time - timestamp)}s > {tolerance_seconds}s"
            )

    expected = compute_signature(payload, signing_secret, timestamp)

    expected_bytes = expected.encode("utf-8")
    provided_bytes = signature.encode("utf-8")

    if not hmac.compare_digest(expected_bytes, provided_bytes):
        raise SignatureVerificationError("Signature mismatch")
