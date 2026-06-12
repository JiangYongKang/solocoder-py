from __future__ import annotations

from typing import Optional

from .exceptions import (
    CRLNotFoundError,
    CRLExpiredError,
    CRLFetchError,
    CertificateNotFoundError,
    EmptyTrustAnchorError,
)
from .models import (
    Certificate,
    CRL,
    CRLFetcher,
    CertChainClock,
)


class TrustAnchorStore:
    def __init__(self) -> None:
        self._anchors: dict[str, Certificate] = {}

    def add(self, cert: Certificate) -> None:
        self._anchors[cert.subject] = cert

    def remove(self, subject: str) -> bool:
        if subject in self._anchors:
            del self._anchors[subject]
            return True
        return False

    def contains(self, subject: str) -> bool:
        return subject in self._anchors

    def get(self, subject: str) -> Optional[Certificate]:
        return self._anchors.get(subject)

    def is_empty(self) -> bool:
        return len(self._anchors) == 0

    def list_subjects(self) -> list[str]:
        return list(self._anchors.keys())

    def check_empty(self) -> None:
        if self.is_empty():
            raise EmptyTrustAnchorError()

    def __len__(self) -> int:
        return len(self._anchors)


class CertificateStore:
    def __init__(self) -> None:
        self._certs_by_subject: dict[str, Certificate] = {}
        self._certs_by_issuer: dict[str, list[Certificate]] = {}

    def add(self, cert: Certificate) -> None:
        self._certs_by_subject[cert.subject] = cert
        if cert.issuer not in self._certs_by_issuer:
            self._certs_by_issuer[cert.issuer] = []
        self._certs_by_issuer[cert.issuer].append(cert)

    def remove(self, subject: str) -> bool:
        cert = self._certs_by_subject.pop(subject, None)
        if cert is None:
            return False
        if cert.issuer in self._certs_by_issuer:
            self._certs_by_issuer[cert.issuer] = [
                c for c in self._certs_by_issuer[cert.issuer] if c.subject != subject
            ]
            if not self._certs_by_issuer[cert.issuer]:
                del self._certs_by_issuer[cert.issuer]
        return True

    def get_by_subject(self, subject: str) -> Optional[Certificate]:
        return self._certs_by_subject.get(subject)

    def find_issuer_cert(self, issuer_name: str) -> Optional[Certificate]:
        return self._certs_by_subject.get(issuer_name)

    def require_issuer_cert(self, issuer_name: str) -> Certificate:
        cert = self.find_issuer_cert(issuer_name)
        if cert is None:
            raise CertificateNotFoundError(issuer_name)
        return cert

    def __len__(self) -> int:
        return len(self._certs_by_subject)


class CRLStore:
    def __init__(
        self,
        clock: CertChainClock,
        fetcher: Optional[CRLFetcher] = None,
        auto_refresh: bool = True,
    ) -> None:
        self._crls: dict[str, CRL] = {}
        self._clock = clock
        self._fetcher = fetcher
        self._auto_refresh = auto_refresh

    def put(self, crl: CRL) -> None:
        self._crls[crl.issuer] = crl

    def remove(self, issuer: str) -> bool:
        if issuer in self._crls:
            del self._crls[issuer]
            return True
        return False

    def has(self, issuer: str) -> bool:
        return issuer in self._crls

    def _refresh(self, issuer: str) -> CRL:
        if self._fetcher is None:
            raise CRLFetchError(issuer, "No CRL fetcher configured")
        try:
            new_crl = self._fetcher.fetch(issuer)
        except Exception as e:
            raise CRLFetchError(issuer, str(e)) from e
        self.put(new_crl)
        return new_crl

    def get_valid(self, issuer: str) -> CRL:
        now = self._clock.now()
        crl = self._crls.get(issuer)
        if crl is None:
            if self._auto_refresh and self._fetcher is not None:
                return self._refresh(issuer)
            raise CRLNotFoundError(issuer)
        if not crl.is_valid_at(now):
            if self._auto_refresh and self._fetcher is not None:
                try:
                    return self._refresh(issuer)
                except CRLFetchError:
                    raise CRLExpiredError(issuer, crl.next_update, now)
            raise CRLExpiredError(issuer, crl.next_update, now)
        return crl

    def get(self, issuer: str) -> Optional[CRL]:
        return self._crls.get(issuer)


__all__ = [
    "TrustAnchorStore",
    "CertificateStore",
    "CRLStore",
]
