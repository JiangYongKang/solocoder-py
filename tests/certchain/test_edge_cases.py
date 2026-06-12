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
    EmptyTrustAnchorError,
    CRLExpiredError,
    ManualClock,
)
from .conftest import MemoryCRLFetcher


class TestValidityBoundarySeconds:
    def test_cert_valid_exactly_at_not_before(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        trust_anchor_store: TrustAnchorStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        root = build_root_cert(base_timestamp, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(base_timestamp, base_timestamp + 3600)

        cert_store = CertificateStore()
        cert_store.add(root)
        cert_store.add(intermediate)
        cert_store.add(leaf)

        trust_anchors = TrustAnchorStore()
        trust_anchors.add(root)

        validator = CertChainValidator(
            trust_anchors=trust_anchors,
            cert_store=cert_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
            enable_crl_check=False,
        )

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf)

        assert result.success is True
        assert leaf.is_valid_at(base_timestamp)

    def test_cert_valid_exactly_at_not_after(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        trust_anchor_store: TrustAnchorStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        root = build_root_cert(base_timestamp, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(base_timestamp, base_timestamp + 3600)

        cert_store = CertificateStore()
        cert_store.add(root)
        cert_store.add(intermediate)
        cert_store.add(leaf)

        trust_anchors = TrustAnchorStore()
        trust_anchors.add(root)

        validator = CertChainValidator(
            trust_anchors=trust_anchors,
            cert_store=cert_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
            enable_crl_check=False,
        )

        manual_clock.set(base_timestamp + 3600)
        result = validator.validate(leaf)

        assert result.success is True
        assert leaf.is_valid_at(base_timestamp + 3600)

    def test_cert_invalid_one_second_before_not_before(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        trust_anchor_store: TrustAnchorStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        root = build_root_cert(base_timestamp - 86400, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp - 86400, base_timestamp + 86400)
        leaf = build_leaf_cert(base_timestamp, base_timestamp + 3600)

        cert_store = CertificateStore()
        cert_store.add(root)
        cert_store.add(intermediate)
        cert_store.add(leaf)

        trust_anchors = TrustAnchorStore()
        trust_anchors.add(root)

        validator = CertChainValidator(
            trust_anchors=trust_anchors,
            cert_store=cert_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
            enable_crl_check=False,
        )

        manual_clock.set(base_timestamp - 1)
        result = validator.validate(leaf)

        assert result.success is False
        assert not leaf.is_valid_at(base_timestamp - 1)

    def test_cert_invalid_one_second_after_not_after(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        trust_anchor_store: TrustAnchorStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        root = build_root_cert(base_timestamp, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(base_timestamp, base_timestamp + 3600)

        cert_store = CertificateStore()
        cert_store.add(root)
        cert_store.add(intermediate)
        cert_store.add(leaf)

        trust_anchors = TrustAnchorStore()
        trust_anchors.add(root)

        validator = CertChainValidator(
            trust_anchors=trust_anchors,
            cert_store=cert_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
            enable_crl_check=False,
        )

        manual_clock.set(base_timestamp + 3600 + 1)
        result = validator.validate(leaf)

        assert result.success is False
        assert not leaf.is_valid_at(base_timestamp + 3600 + 1)

    def test_trust_anchor_validity_boundary(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        root = build_root_cert(base_timestamp, base_timestamp + 3600)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(base_timestamp, base_timestamp + 86400)

        cert_store = CertificateStore()
        cert_store.add(root)
        cert_store.add(intermediate)
        cert_store.add(leaf)

        trust_anchors = TrustAnchorStore()
        trust_anchors.add(root)

        validator = CertChainValidator(
            trust_anchors=trust_anchors,
            cert_store=cert_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
            enable_crl_check=False,
        )

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf)
        assert result.success is True

        manual_clock.set(base_timestamp + 3600 + 1)
        result = validator.validate(leaf)
        assert result.success is False


class TestEmptyTrustAnchor:
    def test_empty_trust_anchor_any_chain_fails(
        self,
        leaf_cert: Certificate,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        empty_anchors = TrustAnchorStore()
        validator = CertChainValidator(
            trust_anchors=empty_anchors,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, EmptyTrustAnchorError)

    def test_empty_trust_anchor_self_signed_fails(
        self,
        root_cert: Certificate,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        empty_anchors = TrustAnchorStore()
        validator = CertChainValidator(
            trust_anchors=empty_anchors,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(root_cert)
        assert result.success is False
        assert isinstance(result.error, EmptyTrustAnchorError)


class TestSingleSelfSignedCert:
    def test_single_self_signed_cert_in_trust_anchors_validates(
        self,
        base_timestamp: float,
        root_secret: bytes,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        single_cert = CertificateBuilder(
            subject="CN=Standalone Root",
            issuer="CN=Standalone Root",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=root_secret,
        ).build()

        trust_anchor_store.add(single_cert)
        certificate_store.add(single_cert)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(single_cert)
        assert result.success is True
        assert len(result.verified_chain) == 1
        assert result.verified_chain[0].subject == "CN=Standalone Root"
        assert result.verified_chain[0].is_self_signed()

    def test_single_self_signed_cert_not_in_trust_anchors_fails(
        self,
        base_timestamp: float,
        root_secret: bytes,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        single_cert = CertificateBuilder(
            subject="CN=Unknown Root",
            issuer="CN=Unknown Root",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400,
            signing_secret=root_secret,
        ).build()

        certificate_store.add(single_cert)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(single_cert)
        assert result.success is False


class TestCRLExpiryRefresh:
    def test_crl_just_expired_triggers_refresh(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        cert_chain_clock: CertChainClock,
        crl_fetcher: MemoryCRLFetcher,
        intermediate_secret: bytes,
        root_secret: bytes,
        leaf_cert: Certificate,
        root_cert: Certificate,
        intermediate_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
    ):
        old_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp - 86400,
            next_update=base_timestamp,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[],
        ).build()

        new_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp,
            next_update=base_timestamp + 86400,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[],
        ).build()

        crl_fetcher.add_crl(root_crl)
        crl_fetcher.add_crl(new_crl)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)
        store.put(root_crl)
        store.put(old_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        manual_clock.set(base_timestamp + 1)
        fetch_count_before = crl_fetcher.get_fetch_count("CN=Intermediate CA")
        result = validator.validate(leaf_cert)
        fetch_count_after = crl_fetcher.get_fetch_count("CN=Intermediate CA")

        assert result.success is True
        assert fetch_count_after == fetch_count_before + 1

        stored_crl = store.get("CN=Intermediate CA")
        assert stored_crl is not None
        assert stored_crl.next_update == base_timestamp + 86400

    def test_crl_expired_no_fetcher_raises(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        cert_chain_clock: CertChainClock,
        intermediate_secret: bytes,
        leaf_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        root_crl,
    ):
        expired_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp - 86400,
            next_update=base_timestamp - 3600,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[],
        ).build()

        store = CRLStore(clock=cert_chain_clock, fetcher=None, auto_refresh=True)
        store.put(root_crl)
        store.put(expired_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        manual_clock.set(base_timestamp)
        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, CRLExpiredError)

    def test_crl_expired_refresh_fails_strict_mode(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        cert_chain_clock: CertChainClock,
        crl_fetcher: MemoryCRLFetcher,
        intermediate_secret: bytes,
        root_secret: bytes,
        leaf_cert: Certificate,
        root_cert: Certificate,
        intermediate_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
    ):
        old_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp - 86400,
            next_update=base_timestamp,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[],
        ).build()

        crl_fetcher.add_crl(root_crl)
        crl_fetcher.set_fail_issuer("CN=Intermediate CA", True)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)
        store.put(root_crl)
        store.put(old_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        manual_clock.set(base_timestamp + 1)
        result = validator.validate(leaf_cert)
        assert result.success is False
        assert isinstance(result.error, CRLExpiredError)

    def test_crl_expired_refresh_fails_lenient_mode(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        cert_chain_clock: CertChainClock,
        crl_fetcher: MemoryCRLFetcher,
        intermediate_secret: bytes,
        leaf_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        root_crl,
    ):
        old_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp - 86400,
            next_update=base_timestamp,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[],
        ).build()

        crl_fetcher.add_crl(root_crl)
        crl_fetcher.set_fail_issuer("CN=Intermediate CA", True)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)
        store.put(root_crl)
        store.put(old_crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=False,
        )

        manual_clock.set(base_timestamp + 1)
        result = validator.validate(leaf_cert)
        assert result.success is True
