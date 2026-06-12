from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from typing import Protocol, Optional

from ..seat.clock import Clock, SystemClock


def _generate_serial() -> int:
    return int.from_bytes(secrets.token_bytes(8), "big")


def _sign_data(data: bytes, secret: bytes) -> bytes:
    return hmac.new(secret, data, hashlib.sha256).digest()


def _verify_signature(data: bytes, signature: bytes, secret: bytes) -> bool:
    expected = _sign_data(data, secret)
    return hmac.compare_digest(expected, signature)


def _cert_tbs_bytes(
    subject: str,
    issuer: str,
    serial_number: int,
    not_before: float,
    not_after: float,
    public_key_id: str,
) -> bytes:
    parts = [
        subject.encode("utf-8"),
        issuer.encode("utf-8"),
        serial_number.to_bytes(16, "big"),
        int(not_before).to_bytes(8, "big"),
        int(not_after).to_bytes(8, "big"),
        public_key_id.encode("utf-8"),
    ]
    return b"|".join(parts)


def _crl_tbs_bytes(
    issuer: str,
    this_update: float,
    next_update: float,
    revoked_serials: list[int],
) -> bytes:
    parts = [
        issuer.encode("utf-8"),
        int(this_update).to_bytes(8, "big"),
        int(next_update).to_bytes(8, "big"),
    ]
    for s in sorted(revoked_serials):
        parts.append(s.to_bytes(16, "big"))
    return b"|".join(parts)


@dataclass
class Certificate:
    subject: str
    issuer: str
    serial_number: int
    not_before: float
    not_after: float
    public_key_id: str
    signature: bytes
    signing_secret: bytes = field(repr=False)

    def is_valid_at(self, time_sec: float) -> bool:
        return self.not_before <= time_sec <= self.not_after

    def is_self_signed(self) -> bool:
        return self.subject == self.issuer

    def tbs_bytes(self) -> bytes:
        return _cert_tbs_bytes(
            self.subject,
            self.issuer,
            self.serial_number,
            self.not_before,
            self.not_after,
            self.public_key_id,
        )

    def verify_signature_against(self, issuer_cert: "Certificate") -> bool:
        return _verify_signature(self.tbs_bytes(), self.signature, issuer_cert.signing_secret)

    def verify_self_signature(self) -> bool:
        return _verify_signature(self.tbs_bytes(), self.signature, self.signing_secret)


class CertificateBuilder:
    def __init__(
        self,
        subject: str,
        issuer: str,
        not_before: float,
        not_after: float,
        signing_secret: bytes,
        public_key_id: Optional[str] = None,
        serial_number: Optional[int] = None,
        subject_signing_secret: Optional[bytes] = None,
    ) -> None:
        if not_before >= not_after:
            raise ValueError("not_before must be earlier than not_after")
        if not subject:
            raise ValueError("subject must not be empty")
        if not issuer:
            raise ValueError("issuer must not be empty")
        if not signing_secret:
            raise ValueError("signing_secret must not be empty")

        self._subject = subject
        self._issuer = issuer
        self._not_before = not_before
        self._not_after = not_after
        self._signing_secret = signing_secret
        self._public_key_id = public_key_id or f"pk-{subject}"
        self._serial_number = serial_number or _generate_serial()
        self._subject_signing_secret = subject_signing_secret

    def build(self) -> Certificate:
        tbs = _cert_tbs_bytes(
            self._subject,
            self._issuer,
            self._serial_number,
            self._not_before,
            self._not_after,
            self._public_key_id,
        )
        signature = _sign_data(tbs, self._signing_secret)
        stored_secret = self._subject_signing_secret or self._signing_secret
        return Certificate(
            subject=self._subject,
            issuer=self._issuer,
            serial_number=self._serial_number,
            not_before=self._not_before,
            not_after=self._not_after,
            public_key_id=self._public_key_id,
            signature=signature,
            signing_secret=stored_secret,
        )


@dataclass
class CRL:
    issuer: str
    this_update: float
    next_update: float
    revoked_serials: list[int]
    signature: bytes
    issuer_signing_secret: bytes = field(repr=False)

    def is_valid_at(self, time_sec: float) -> bool:
        return self.this_update <= time_sec <= self.next_update

    def is_revoked(self, serial_number: int) -> bool:
        return serial_number in self.revoked_serials

    def tbs_bytes(self) -> bytes:
        return _crl_tbs_bytes(
            self.issuer, self.this_update, self.next_update, self.revoked_serials
        )

    def verify_signature_against(self, issuer_cert: Certificate) -> bool:
        return _verify_signature(
            self.tbs_bytes(), self.signature, issuer_cert.signing_secret
        )


class CRLBuilder:
    def __init__(
        self,
        issuer: str,
        this_update: float,
        next_update: float,
        issuer_signing_secret: bytes,
        revoked_serials: Optional[list[int]] = None,
    ) -> None:
        if this_update >= next_update:
            raise ValueError("this_update must be earlier than next_update")
        if not issuer:
            raise ValueError("issuer must not be empty")
        if not issuer_signing_secret:
            raise ValueError("issuer_signing_secret must not be empty")

        self._issuer = issuer
        self._this_update = this_update
        self._next_update = next_update
        self._issuer_signing_secret = issuer_signing_secret
        self._revoked_serials = sorted(revoked_serials or [])

    def build(self) -> CRL:
        tbs = _crl_tbs_bytes(
            self._issuer, self._this_update, self._next_update, self._revoked_serials
        )
        signature = _sign_data(tbs, self._issuer_signing_secret)
        return CRL(
            issuer=self._issuer,
            this_update=self._this_update,
            next_update=self._next_update,
            revoked_serials=list(self._revoked_serials),
            signature=signature,
            issuer_signing_secret=self._issuer_signing_secret,
        )


class CRLFetcher(Protocol):
    def fetch(self, issuer: str) -> CRL:
        ...


class CertChainClock:
    def __init__(self, clock: Optional[Clock] = None) -> None:
        self._clock: Clock = clock or SystemClock()

    def now(self) -> float:
        return self._clock.now()

    @classmethod
    def from_clock(cls, clock: Clock) -> "CertChainClock":
        return cls(clock)


class ValidationResult:
    def __init__(
        self,
        success: bool,
        verified_chain: Optional[list[Certificate]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self.success = success
        self.verified_chain = verified_chain or []
        self.error = error

    def __bool__(self) -> bool:
        return self.success

    def __repr__(self) -> str:
        if self.success:
            return f"ValidationResult(success=True, chain_length={len(self.verified_chain)})"
        return f"ValidationResult(success=False, error={type(self.error).__name__}: {self.error})"


__all__ = [
    "Certificate",
    "CertificateBuilder",
    "CRL",
    "CRLBuilder",
    "CRLFetcher",
    "CertChainClock",
    "ValidationResult",
    "_generate_serial",
    "_sign_data",
    "_verify_signature",
]
