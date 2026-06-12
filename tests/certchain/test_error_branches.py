from __future__ import annotations

import pytest

from solocoder_py.certchain import (
    Certificate,
    CertificateBuilder,
    CRLBuilder,
    CertChainClock,
    CertChainValidator,
    CertificateStore,
    CRLStore,
    TrustAnchorStore,
    CertificateExpiredError,
    CertificateNotYetValidError,
    CertificateRevokedError,
    ChainBrokenError,
    InvalidSignatureError,
    TrustAnchorNotFoundError,
    CRLFetchError,
    CRLExpiredError,
    ManualClock,
)
from .conftest import MemoryCRLFetcher


class TestCertificateExpired:
    def test_leaf_cert_expired(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        leaf_cert: Certificate,
        validator: CertChainValidator,
    ):
        leaf_cert.not_before = base_timestamp - 86400
        leaf_cert.not_after = base_timestamp - 3600

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf_cert)

        assert result.success is False
        assert isinstance(result.error, CertificateExpiredError)
        assert result.error.subject == "CN=example.com"

    def test_intermediate_cert_expired(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        leaf_cert: Certificate,
        intermediate_cert: Certificate,
        validator: CertChainValidator,
    ):
        intermediate_cert.not_before = base_timestamp - 86400
        intermediate_cert.not_after = base_timestamp - 3600

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf_cert)

        assert result.success is False
        assert isinstance(result.error, CertificateExpiredError)
        assert result.error.subject == "CN=Intermediate CA"

    def test_root_cert_expired(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        leaf_cert: Certificate,
        root_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        root_cert.not_before = base_timestamp - 86400
        root_cert.not_after = base_timestamp - 3600

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf_cert)

        assert result.success is False
        assert isinstance(result.error, CertificateExpiredError)
        assert result.error.subject == "CN=Root CA"


class TestCertificateNotYetValid:
    def test_leaf_cert_not_yet_valid(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        leaf_cert: Certificate,
        validator: CertChainValidator,
    ):
        leaf_cert.not_before = base_timestamp + 3600
        leaf_cert.not_after = base_timestamp + 86400

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf_cert)

        assert result.success is False
        assert isinstance(result.error, CertificateNotYetValidError)
        assert result.error.subject == "CN=example.com"

    def test_intermediate_cert_not_yet_valid(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        leaf_cert: Certificate,
        intermediate_cert: Certificate,
        validator: CertChainValidator,
    ):
        intermediate_cert.not_before = base_timestamp + 3600
        intermediate_cert.not_after = base_timestamp + 86400

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf_cert)

        assert result.success is False
        assert isinstance(result.error, CertificateNotYetValidError)
        assert result.error.subject == "CN=Intermediate CA"


class TestCertificateRevoked:
    def test_leaf_cert_revoked_in_crl(
        self,
        base_timestamp: float,
        leaf_cert: Certificate,
        intermediate_secret: bytes,
        crl_fetcher: MemoryCRLFetcher,
        cert_chain_clock: CertChainClock,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
    ):
        revoked_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp,
            next_update=base_timestamp + 86400,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[leaf_cert.serial_number],
        ).build()

        crl_fetcher.add_crl(root_crl)
        crl_fetcher.add_crl(revoked_crl)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher)
        store.put(root_crl)
        store.put(revoked_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, CertificateRevokedError)
        assert result.error.subject == "CN=example.com"
        assert result.error.serial_number == leaf_cert.serial_number

    def test_intermediate_cert_revoked_in_crl(
        self,
        base_timestamp: float,
        leaf_cert: Certificate,
        intermediate_cert: Certificate,
        root_secret: bytes,
        crl_fetcher: MemoryCRLFetcher,
        cert_chain_clock: CertChainClock,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        intermediate_crl,
    ):
        revoked_crl = CRLBuilder(
            issuer="CN=Root CA",
            this_update=base_timestamp,
            next_update=base_timestamp + 86400,
            issuer_signing_secret=root_secret,
            revoked_serials=[intermediate_cert.serial_number],
        ).build()

        crl_fetcher.add_crl(revoked_crl)
        crl_fetcher.add_crl(intermediate_crl)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher)
        store.put(revoked_crl)
        store.put(intermediate_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, CertificateRevokedError)
        assert result.error.subject == "CN=Intermediate CA"
        assert result.error.serial_number == intermediate_cert.serial_number


class TestTrustAnchorNotFound:
    def test_chain_top_issuer_not_in_trust_anchors(
        self,
        base_timestamp: float,
        leaf_cert: Certificate,
        intermediate_cert: Certificate,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        other_secret = b"other-root-secret-12345"
        other_root = CertificateBuilder(
            subject="CN=Other Root",
            issuer="CN=Other Root",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400 * 365,
            signing_secret=other_secret,
        ).build()

        anchors = TrustAnchorStore()
        anchors.add(other_root)

        validator = CertChainValidator(
            trust_anchors=anchors,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, TrustAnchorNotFoundError)
        assert result.error.top_subject == "CN=Root CA"
        assert result.error.top_issuer == "CN=Root CA"

    def test_self_signed_cert_not_in_trust_anchors(
        self,
        base_timestamp: float,
        root_secret: bytes,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        unknown_root = CertificateBuilder(
            subject="CN=Unknown Root",
            issuer="CN=Unknown Root",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=root_secret,
        ).build()

        certificate_store.add(unknown_root)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(unknown_root)
        assert result.success is False
        assert isinstance(result.error, TrustAnchorNotFoundError)


class TestChainBroken:
    def test_issuer_cert_not_found_in_store(
        self,
        leaf_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
        root_cert: Certificate,
    ):
        incomplete_store = CertificateStore()
        incomplete_store.add(leaf_cert)
        incomplete_store.add(root_cert)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=incomplete_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, ChainBrokenError)
        assert result.error.subject == "CN=example.com"
        assert result.error.issuer == "CN=Intermediate CA"

    def test_circular_chain_detection(
        self,
        base_timestamp: float,
        trust_anchor_store: TrustAnchorStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        secret_a = b"secret-a"
        secret_b = b"secret-b"

        cert_a = CertificateBuilder(
            subject="CN=Cert A",
            issuer="CN=Cert B",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=secret_b,
            subject_signing_secret=secret_a,
        ).build()

        cert_b = CertificateBuilder(
            subject="CN=Cert B",
            issuer="CN=Cert A",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=secret_a,
            subject_signing_secret=secret_b,
        ).build()

        store = CertificateStore()
        store.add(cert_a)
        store.add(cert_b)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(cert_a)
        assert result.success is False
        assert isinstance(result.error, ChainBrokenError)


class TestInvalidSignature:
    def test_leaf_signature_does_not_match_issuer(
        self,
        base_timestamp: float,
        intermediate_cert: Certificate,
        root_secret: bytes,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        wrong_secret = b"wrong-secret-1234567890"
        tampered_leaf = CertificateBuilder(
            subject="CN=example.com",
            issuer="CN=Intermediate CA",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=wrong_secret,
        ).build()

        certificate_store.add(tampered_leaf)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(tampered_leaf)
        assert result.success is False
        assert isinstance(result.error, InvalidSignatureError)
        assert result.error.subject == "CN=example.com"
        assert result.error.claimed_issuer == "CN=Intermediate CA"

    def test_intermediate_signature_does_not_match_root(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        root_cert: Certificate,
        wrong_secret: bytes = b"wrong-secret-12345",
    ):
        tampered_intermediate = CertificateBuilder(
            subject="CN=Intermediate CA",
            issuer="CN=Root CA",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=wrong_secret,
        ).build()

        anchors = TrustAnchorStore()
        anchors.add(root_cert)

        store = CertificateStore()
        store.add(root_cert)
        store.add(tampered_intermediate)

        clock = CertChainClock.from_clock(manual_clock)
        crl_store = CRLStore(clock=clock, fetcher=None, auto_refresh=False)

        validator = CertChainValidator(
            trust_anchors=anchors,
            cert_store=store,
            crl_store=crl_store,
            clock=clock,
            enable_crl_check=False,
        )

        result = validator.validate(tampered_intermediate)
        assert result.success is False
        assert isinstance(result.error, InvalidSignatureError)
        assert result.error.subject == "CN=Intermediate CA"
        assert result.error.claimed_issuer == "CN=Root CA"

    def test_cert_signed_by_wrong_issuer_name(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        root_cert: Certificate,
        intermediate_cert: Certificate,
        root_secret: bytes,
    ):
        leaf = CertificateBuilder(
            subject="CN=example.com",
            issuer="CN=Wrong CA",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=root_secret,
        ).build()

        anchors = TrustAnchorStore()
        anchors.add(root_cert)

        store = CertificateStore()
        store.add(root_cert)
        store.add(intermediate_cert)
        store.add(leaf)

        clock = CertChainClock.from_clock(manual_clock)
        crl_store = CRLStore(clock=clock, fetcher=None, auto_refresh=False)

        validator = CertChainValidator(
            trust_anchors=anchors,
            cert_store=store,
            crl_store=crl_store,
            clock=clock,
            enable_crl_check=False,
        )

        result = validator.validate(leaf)
        assert result.success is False
        assert isinstance(result.error, ChainBrokenError)


class TestCRLFetchFailure:
    def test_crl_fetch_failure_lenient_mode_passes(
        self,
        leaf_cert: Certificate,
        crl_fetcher: MemoryCRLFetcher,
        cert_chain_clock: CertChainClock,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
        intermediate_crl,
    ):
        crl_fetcher.add_crl(root_crl)
        crl_fetcher.add_crl(intermediate_crl)
        crl_fetcher.set_fail_issuer("CN=Intermediate CA", True)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=False)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=False,
        )

        result = validator.validate(leaf_cert)
        assert result.success is True

    def test_crl_fetch_failure_strict_mode_fails(
        self,
        leaf_cert: Certificate,
        crl_fetcher: MemoryCRLFetcher,
        cert_chain_clock: CertChainClock,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
        intermediate_crl,
    ):
        crl_fetcher.add_crl(root_crl)
        crl_fetcher.add_crl(intermediate_crl)
        crl_fetcher.set_fail_issuer("CN=Intermediate CA", True)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, CRLFetchError)

    def test_crl_not_found_lenient_mode_passes(
        self,
        leaf_cert: Certificate,
        crl_fetcher: MemoryCRLFetcher,
        cert_chain_clock: CertChainClock,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
    ):
        crl_fetcher.add_crl(root_crl)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)
        store.put(root_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=False,
        )

        result = validator.validate(leaf_cert)
        assert result.success is True

    def test_crl_not_found_strict_mode_fails(
        self,
        leaf_cert: Certificate,
        crl_fetcher: MemoryCRLFetcher,
        cert_chain_clock: CertChainClock,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
    ):
        crl_fetcher.add_crl(root_crl)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)
        store.put(root_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, CRLFetchError)
