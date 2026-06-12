from __future__ import annotations

from typing import Optional, Callable

import pytest

from solocoder_py.certchain import (
    Certificate,
    CertificateBuilder,
    CRL,
    CRLBuilder,
    CRLFetcher,
    CertChainClock,
    CertChainValidator,
    CertificateStore,
    CRLStore,
    TrustAnchorStore,
    ManualClock,
)


@pytest.fixture
def base_timestamp() -> float:
    return 1718150400.0


@pytest.fixture
def manual_clock(base_timestamp: float) -> ManualClock:
    return ManualClock(start_time=base_timestamp)


@pytest.fixture
def cert_chain_clock(manual_clock: ManualClock) -> CertChainClock:
    return CertChainClock.from_clock(manual_clock)


@pytest.fixture
def root_secret() -> bytes:
    return b"root-secret-key-1234567890"


@pytest.fixture
def intermediate_secret() -> bytes:
    return b"intermediate-secret-key-0987654321"


@pytest.fixture
def leaf_secret() -> bytes:
    return b"leaf-secret-key-abcdefghij"


@pytest.fixture
def build_root_cert(root_secret: bytes) -> Callable:
    def _build(not_before: float, not_after: float) -> Certificate:
        return CertificateBuilder(
            subject="CN=Root CA",
            issuer="CN=Root CA",
            not_before=not_before,
            not_after=not_after,
            signing_secret=root_secret,
        ).build()
    return _build


@pytest.fixture
def root_cert(base_timestamp: float, build_root_cert: Callable) -> Certificate:
    return build_root_cert(base_timestamp, base_timestamp + 86400 * 365)


@pytest.fixture
def build_intermediate_cert(root_secret: bytes, intermediate_secret: bytes) -> Callable:
    def _build(not_before: float, not_after: float) -> Certificate:
        return CertificateBuilder(
            subject="CN=Intermediate CA",
            issuer="CN=Root CA",
            not_before=not_before,
            not_after=not_after,
            signing_secret=root_secret,
            subject_signing_secret=intermediate_secret,
            public_key_id="pk-intermediate",
        ).build()
    return _build


@pytest.fixture
def intermediate_cert(
    base_timestamp: float,
    build_intermediate_cert: Callable,
) -> Certificate:
    return build_intermediate_cert(base_timestamp, base_timestamp + 86400 * 180)


@pytest.fixture
def build_leaf_cert(intermediate_secret: bytes) -> Callable:
    def _build(not_before: float, not_after: float) -> Certificate:
        return CertificateBuilder(
            subject="CN=example.com",
            issuer="CN=Intermediate CA",
            not_before=not_before,
            not_after=not_after,
            signing_secret=intermediate_secret,
            public_key_id="pk-example",
        ).build()
    return _build


@pytest.fixture
def leaf_cert(
    base_timestamp: float,
    build_leaf_cert: Callable,
) -> Certificate:
    return build_leaf_cert(base_timestamp, base_timestamp + 86400 * 90)


@pytest.fixture
def trust_anchor_store(root_cert: Certificate) -> TrustAnchorStore:
    store = TrustAnchorStore()
    store.add(root_cert)
    return store


@pytest.fixture
def certificate_store(
    root_cert: Certificate,
    intermediate_cert: Certificate,
    leaf_cert: Certificate,
) -> CertificateStore:
    store = CertificateStore()
    store.add(root_cert)
    store.add(intermediate_cert)
    store.add(leaf_cert)
    return store


class MemoryCRLFetcher:
    def __init__(self) -> None:
        self._crls: dict[str, CRL] = {}
        self._fail_issuers: set[str] = set()
        self._fetch_count: dict[str, int] = {}

    def add_crl(self, crl: CRL) -> None:
        self._crls[crl.issuer] = crl

    def set_fail_issuer(self, issuer: str, fail: bool = True) -> None:
        if fail:
            self._fail_issuers.add(issuer)
        else:
            self._fail_issuers.discard(issuer)

    def get_fetch_count(self, issuer: str) -> int:
        return self._fetch_count.get(issuer, 0)

    def fetch(self, issuer: str) -> CRL:
        self._fetch_count[issuer] = self._fetch_count.get(issuer, 0) + 1
        if issuer in self._fail_issuers:
            raise RuntimeError(f"Failed to fetch CRL for {issuer}")
        if issuer not in self._crls:
            raise RuntimeError(f"CRL not found for {issuer}")
        return self._crls[issuer]


@pytest.fixture
def crl_fetcher() -> MemoryCRLFetcher:
    return MemoryCRLFetcher()


@pytest.fixture
def root_crl(
    base_timestamp: float,
    root_secret: bytes,
) -> CRL:
    return CRLBuilder(
        issuer="CN=Root CA",
        this_update=base_timestamp,
        next_update=base_timestamp + 86400,
        issuer_signing_secret=root_secret,
        revoked_serials=[],
    ).build()


@pytest.fixture
def intermediate_crl(
    base_timestamp: float,
    intermediate_secret: bytes,
) -> CRL:
    return CRLBuilder(
        issuer="CN=Intermediate CA",
        this_update=base_timestamp,
        next_update=base_timestamp + 86400,
        issuer_signing_secret=intermediate_secret,
        revoked_serials=[],
    ).build()


@pytest.fixture
def crl_store(
    cert_chain_clock: CertChainClock,
    crl_fetcher: MemoryCRLFetcher,
    root_crl: CRL,
    intermediate_crl: CRL,
) -> CRLStore:
    crl_fetcher.add_crl(root_crl)
    crl_fetcher.add_crl(intermediate_crl)
    store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)
    store.put(root_crl)
    store.put(intermediate_crl)
    return store


@pytest.fixture
def validator(
    trust_anchor_store: TrustAnchorStore,
    certificate_store: CertificateStore,
    crl_store: CRLStore,
    cert_chain_clock: CertChainClock,
) -> CertChainValidator:
    return CertChainValidator(
        trust_anchors=trust_anchor_store,
        cert_store=certificate_store,
        crl_store=crl_store,
        clock=cert_chain_clock,
        enable_crl_check=True,
        strict_crl=False,
    )
