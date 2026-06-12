from __future__ import annotations

import pytest

from solocoder_py.certchain import (
    Certificate,
    CertificateBuilder,
    CRL,
    CRLBuilder,
    CertChainClock,
    CertChainValidator,
    CertificateStore,
    CRLStore,
    TrustAnchorStore,
    EmptyTrustAnchorError,
    CRLExpiredError,
    CRLFetchError,
    CertificateExpiredError,
    CertificateNotYetValidError,
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

    def test_not_after_dot_zero_now_dot_nine_expired(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        nb = base_timestamp + 0.0
        na = base_timestamp + 3600.0
        root = build_root_cert(base_timestamp, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(nb, na)

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

        now = na + 0.9
        manual_clock.set(now)
        result = validator.validate(leaf)

        assert result.success is False
        assert not leaf.is_valid_at(now)

    def test_not_before_dot_nine_now_dot_one_not_yet_valid(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        nb = base_timestamp + 1000.9
        na = base_timestamp + 5000.0
        root = build_root_cert(base_timestamp, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(nb, na)

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

        now = base_timestamp + 1000.1
        manual_clock.set(now)
        result = validator.validate(leaf)

        assert result.success is False
        assert not leaf.is_valid_at(now)

    def test_not_after_dot_nine_now_dot_zero_valid(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        nb = base_timestamp + 0.0
        na = base_timestamp + 3600.9
        root = build_root_cert(base_timestamp, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(nb, na)

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

        now = base_timestamp + 3600.0
        manual_clock.set(now)
        result = validator.validate(leaf)

        assert result.success is True
        assert leaf.is_valid_at(now)

    def test_not_before_dot_one_now_dot_nine_valid(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        nb = base_timestamp + 1000.1
        na = base_timestamp + 5000.0
        root = build_root_cert(base_timestamp, base_timestamp + 86400)
        intermediate = build_intermediate_cert(base_timestamp, base_timestamp + 86400)
        leaf = build_leaf_cert(nb, na)

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

        now = base_timestamp + 1000.9
        manual_clock.set(now)
        result = validator.validate(leaf)

        assert result.success is True
        assert leaf.is_valid_at(now)

    def test_is_valid_at_subsecond_boundary_direct(
        self,
        base_timestamp: float,
        root_secret: bytes,
    ):
        cert = CertificateBuilder(
            subject="CN=subsec.example",
            issuer="CN=subsec-ca",
            not_before=1000.9,
            not_after=2000.0,
            signing_secret=root_secret,
        ).build()

        assert not cert.is_valid_at(1000.1)
        assert cert.is_valid_at(1000.9)
        assert cert.is_valid_at(1000.95)
        assert cert.is_valid_at(2000.0)
        assert not cert.is_valid_at(2000.9)
        assert cert.is_valid_at(1500.5)

    def test_subsecond_difference_produces_different_signature(
        self,
        root_secret: bytes,
    ):
        cert_a = CertificateBuilder(
            subject="CN=same-subject",
            issuer="CN=same-issuer",
            not_before=1000.0,
            not_after=2000.0,
            signing_secret=root_secret,
            serial_number=42,
            public_key_id="pk-same",
        ).build()

        cert_b = CertificateBuilder(
            subject="CN=same-subject",
            issuer="CN=same-issuer",
            not_before=1000.1,
            not_after=2000.0,
            signing_secret=root_secret,
            serial_number=42,
            public_key_id="pk-same",
        ).build()

        assert cert_a.tbs_bytes() != cert_b.tbs_bytes()
        assert cert_a.signature != cert_b.signature

    def test_subsecond_not_after_difference_produces_different_signature(
        self,
        root_secret: bytes,
    ):
        cert_a = CertificateBuilder(
            subject="CN=same-subject",
            issuer="CN=same-issuer",
            not_before=1000.0,
            not_after=2000.0,
            signing_secret=root_secret,
            serial_number=42,
            public_key_id="pk-same",
        ).build()

        cert_b = CertificateBuilder(
            subject="CN=same-subject",
            issuer="CN=same-issuer",
            not_before=1000.0,
            not_after=2000.9,
            signing_secret=root_secret,
            serial_number=42,
            public_key_id="pk-same",
        ).build()

        assert cert_a.tbs_bytes() != cert_b.tbs_bytes()
        assert cert_a.signature != cert_b.signature

    def test_crl_subsecond_difference_produces_different_signature(
        self,
        root_secret: bytes,
    ):
        crl_a = CRLBuilder(
            issuer="CN=same-ca",
            this_update=1000.0,
            next_update=2000.0,
            issuer_signing_secret=root_secret,
            revoked_serials=[1, 2, 3],
        ).build()

        crl_b = CRLBuilder(
            issuer="CN=same-ca",
            this_update=1000.1,
            next_update=2000.0,
            issuer_signing_secret=root_secret,
            revoked_serials=[1, 2, 3],
        ).build()

        assert crl_a.tbs_bytes() != crl_b.tbs_bytes()
        assert crl_a.signature != crl_b.signature

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

    def test_trust_anchor_subsecond_expiry(
        self,
        base_timestamp: float,
        manual_clock: ManualClock,
        build_leaf_cert,
        build_intermediate_cert,
        build_root_cert,
        crl_store: CRLStore,
        cert_chain_clock: CertChainClock,
    ):
        root_not_after = base_timestamp + 3600.0
        root = build_root_cert(base_timestamp, root_not_after)
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

        manual_clock.set(root_not_after + 0.9)
        result = validator.validate(leaf)
        assert result.success is False
        assert isinstance(result.error, CertificateExpiredError)
        assert result.error.subject == "CN=Root CA"


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

    def test_crl_next_update_dot_zero_now_dot_nine_triggers_refresh(
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
            next_update=base_timestamp + 3600.0,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[],
        ).build()

        new_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp + 3600.0,
            next_update=base_timestamp + 3600.0 + 86400,
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

        now = base_timestamp + 3600.9
        manual_clock.set(now)
        fetch_count_before = crl_fetcher.get_fetch_count("CN=Intermediate CA")
        result = validator.validate(leaf_cert)
        fetch_count_after = crl_fetcher.get_fetch_count("CN=Intermediate CA")

        assert result.success is True
        assert fetch_count_after == fetch_count_before + 1

    def test_crl_next_update_dot_nine_now_dot_zero_still_valid(
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
        crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp - 86400,
            next_update=base_timestamp + 3600.9,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[],
        ).build()

        crl_fetcher.add_crl(root_crl)

        store = CRLStore(clock=cert_chain_clock, fetcher=crl_fetcher, auto_refresh=True)
        store.put(root_crl)
        store.put(crl)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=store,
            clock=cert_chain_clock,
            strict_crl=True,
        )

        now = base_timestamp + 3600.0
        manual_clock.set(now)
        fetch_count_before = crl_fetcher.get_fetch_count("CN=Intermediate CA")
        result = validator.validate(leaf_cert)
        fetch_count_after = crl_fetcher.get_fetch_count("CN=Intermediate CA")

        assert result.success is True
        assert fetch_count_after == fetch_count_before

    def test_crl_is_valid_at_subsecond_boundary(
        self,
        intermediate_secret: bytes,
    ):
        crl = CRLBuilder(
            issuer="CN=Test CA",
            this_update=1000.9,
            next_update=2000.0,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[1, 2],
        ).build()

        assert not crl.is_valid_at(1000.1)
        assert crl.is_valid_at(1000.9)
        assert crl.is_valid_at(1000.95)
        assert crl.is_valid_at(2000.0)
        assert not crl.is_valid_at(2000.9)
        assert crl.is_valid_at(1500.5)
