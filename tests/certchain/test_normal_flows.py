from __future__ import annotations

import pytest

from solocoder_py.certchain import (
    Certificate,
    CertificateBuilder,
    CRLBuilder,
    CertChainValidator,
    CertificateStore,
    CRLStore,
    TrustAnchorStore,
    CertificateRevokedError,
    TrustAnchorNotFoundError,
)
from .conftest import MemoryCRLFetcher


class TestThreeLevelChain:
    def test_leaf_to_intermediate_to_root_validates(
        self,
        validator: CertChainValidator,
        leaf_cert: Certificate,
        intermediate_cert: Certificate,
        root_cert: Certificate,
    ):
        result = validator.validate(leaf_cert)

        assert result.success is True
        assert len(result.verified_chain) == 3
        assert result.verified_chain[0].subject == "CN=example.com"
        assert result.verified_chain[1].subject == "CN=Intermediate CA"
        assert result.verified_chain[2].subject == "CN=Root CA"

    def test_chain_signatures_are_verified(
        self,
        validator: CertChainValidator,
        leaf_cert: Certificate,
        intermediate_cert: Certificate,
        root_cert: Certificate,
    ):
        result = validator.validate(leaf_cert)
        chain = result.verified_chain

        assert chain[0].verify_signature_against(chain[1])
        assert chain[1].verify_signature_against(chain[2])
        assert chain[2].verify_self_signature()


class TestSelfSignedRootInTrustAnchor:
    def test_self_signed_trust_anchor_validates(
        self,
        root_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock,
    ):
        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(root_cert)

        assert result.success is True
        assert len(result.verified_chain) == 1
        assert result.verified_chain[0].subject == "CN=Root CA"
        assert result.verified_chain[0].is_self_signed()

    def test_self_signed_chain_no_duplicate_anchor(
        self,
        root_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock,
    ):
        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result = validator.validate(root_cert)

        assert result.success is True
        subjects = [c.subject for c in result.verified_chain]
        assert subjects.count("CN=Root CA") == 1


class TestCRLNotContainingCert:
    def test_crl_empty_cert_validates(
        self,
        validator: CertChainValidator,
        leaf_cert: Certificate,
    ):
        result = validator.validate(leaf_cert)
        assert result.success is True

    def test_crl_contains_other_serial_not_target(
        self,
        base_timestamp: float,
        intermediate_secret: bytes,
        crl_fetcher: MemoryCRLFetcher,
        cert_chain_clock,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        leaf_cert: Certificate,
        root_crl,
        intermediate_cert: Certificate,
        root_secret: bytes,
        root_cert: Certificate,
    ):
        other_serial = leaf_cert.serial_number + 1
        revoked_crl = CRLBuilder(
            issuer="CN=Intermediate CA",
            this_update=base_timestamp,
            next_update=base_timestamp + 86400,
            issuer_signing_secret=intermediate_secret,
            revoked_serials=[other_serial],
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
        )

        result = validator.validate(leaf_cert)
        assert result.success is True


class TestTrustAnchorChanges:
    def test_remove_trust_anchor_causes_failure(
        self,
        base_timestamp: float,
        leaf_cert: Certificate,
        root_cert: Certificate,
        trust_anchor_store: TrustAnchorStore,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock,
    ):
        other_secret = b"other-root-secret-12345"
        other_root = CertificateBuilder(
            subject="CN=Other Root",
            issuer="CN=Other Root",
            not_before=base_timestamp,
            not_after=base_timestamp + 86400 * 365,
            signing_secret=other_secret,
        ).build()
        trust_anchor_store.add(other_root)

        validator = CertChainValidator(
            trust_anchors=trust_anchor_store,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result_before = validator.validate(leaf_cert)
        assert result_before.success is True

        trust_anchor_store.remove(root_cert.subject)

        result_after = validator.validate(leaf_cert)
        assert result_after.success is False
        assert isinstance(result_after.error, TrustAnchorNotFoundError)

    def test_add_trust_anchor_enables_validation(
        self,
        leaf_cert: Certificate,
        root_cert: Certificate,
        intermediate_cert: Certificate,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock,
    ):
        empty_anchors = TrustAnchorStore()
        validator = CertChainValidator(
            trust_anchors=empty_anchors,
            cert_store=certificate_store,
            crl_store=crl_store,
            clock=cert_chain_clock,
        )

        result_before = validator.validate(leaf_cert)
        assert result_before.success is False

        empty_anchors.add(root_cert)

        result_after = validator.validate(leaf_cert)
        assert result_after.success is True
        assert len(result_after.verified_chain) == 3

    def test_switch_trust_anchor_to_different_root(
        self,
        base_timestamp: float,
        leaf_cert: Certificate,
        intermediate_cert: Certificate,
        certificate_store: CertificateStore,
        crl_store: CRLStore,
        cert_chain_clock,
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
