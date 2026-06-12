from __future__ import annotations

from typing import Optional

from .exceptions import (
    CertificateExpiredError,
    CertificateNotYetValidError,
    CertificateRevokedError,
    ChainBrokenError,
    InvalidSignatureError,
    TrustAnchorNotFoundError,
)
from .models import (
    Certificate,
    CertChainClock,
    CRLFetcher,
    ValidationResult,
)
from .store import (
    CertificateStore,
    CRLStore,
    TrustAnchorStore,
)


class CertChainValidator:
    def __init__(
        self,
        trust_anchors: TrustAnchorStore,
        cert_store: CertificateStore,
        crl_store: CRLStore,
        clock: Optional[CertChainClock] = None,
        enable_crl_check: bool = True,
        strict_crl: bool = False,
    ) -> None:
        self._trust_anchors = trust_anchors
        self._cert_store = cert_store
        self._crl_store = crl_store
        self._clock = clock or CertChainClock()
        self._enable_crl_check = enable_crl_check
        self._strict_crl = strict_crl

    def validate(self, leaf_cert: Certificate) -> ValidationResult:
        try:
            chain = self._build_and_verify_chain(leaf_cert)
            return ValidationResult(success=True, verified_chain=chain)
        except Exception as e:
            return ValidationResult(success=False, error=e)

    def _build_and_verify_chain(self, leaf_cert: Certificate) -> list[Certificate]:
        self._trust_anchors.check_empty()
        now = self._clock.now()

        chain: list[Certificate] = []
        current: Optional[Certificate] = leaf_cert
        visited: set[str] = set()

        while current is not None:
            if current.subject in visited:
                raise ChainBrokenError(current.subject, current.issuer)
            visited.add(current.subject)

            self._check_validity(current, now)

            if chain:
                prev = chain[-1]
                if not prev.verify_signature_against(current):
                    raise InvalidSignatureError(prev.subject, prev.issuer)

            if self._enable_crl_check:
                self._check_crl(current, now)

            chain.append(current)

            if self._trust_anchors.contains(current.issuer):
                anchor = self._trust_anchors.get(current.issuer)
                if anchor is None:
                    raise TrustAnchorNotFoundError(current.subject, current.issuer)

                self._check_validity(anchor, now)

                if not current.verify_signature_against(anchor):
                    raise InvalidSignatureError(current.subject, current.issuer)

                if current.subject != anchor.subject:
                    chain.append(anchor)

                return chain

            if current.is_self_signed():
                if self._trust_anchors.contains(current.subject):
                    if not current.verify_self_signature():
                        raise InvalidSignatureError(current.subject, current.issuer)
                    return chain
                raise TrustAnchorNotFoundError(current.subject, current.issuer)

            next_cert = self._cert_store.find_issuer_cert(current.issuer)
            if next_cert is None:
                raise ChainBrokenError(current.subject, current.issuer)

            if next_cert.subject != current.issuer:
                raise ChainBrokenError(current.subject, current.issuer)

            current = next_cert

        raise TrustAnchorNotFoundError(leaf_cert.subject, "unknown")

    def _check_validity(self, cert: Certificate, now: float) -> None:
        if now < cert.not_before:
            raise CertificateNotYetValidError(cert.subject, cert.not_before, now)
        if now > cert.not_after:
            raise CertificateExpiredError(cert.subject, cert.not_after, now)

    def _check_crl(self, cert: Certificate, now: float) -> None:
        if cert.is_self_signed() and self._trust_anchors.contains(cert.subject):
            return

        try:
            crl = self._crl_store.get_valid(cert.issuer)
        except Exception as e:
            if self._strict_crl:
                raise
            return

        if crl.is_revoked(cert.serial_number):
            raise CertificateRevokedError(cert.subject, cert.serial_number, cert.issuer)


__all__ = ["CertChainValidator"]
