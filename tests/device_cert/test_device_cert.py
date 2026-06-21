from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from solocoder_py.device_cert import (
    CSR,
    CertificateIssuanceResult,
    CertificateStatus,
    DeviceCertService,
    DeviceNotFoundError,
    DeviceNotRegisteredError,
    DeviceRevokedError,
    DeviceRecord,
    DeviceStatus,
    DuplicateDeviceError,
    InMemoryDeviceCertStore,
    InvalidPSKError,
    RegistrationResult,
    CertificateNotFoundError,
    DEFAULT_CA_ISSUER,
    DEFAULT_CERT_VALIDITY_DAYS,
)


VALID_PSK_LIST = {"psk-alpha-001", "psk-beta-002", "psk-gamma-003"}


class TestPSKRegistration:
    def test_register_with_valid_psk(self, make_service):
        service = make_service()
        result = service.register_device("sensor-01", "psk-alpha-001")

        assert isinstance(result, RegistrationResult)
        assert result.device_identifier == "sensor-01"
        assert result.device_id.startswith("dev-")
        assert isinstance(result.registered_at, datetime)

    def test_register_generates_unique_device_id(self, make_service):
        service = make_service()
        r1 = service.register_device("sensor-01", "psk-alpha-001")
        r2 = service.register_device("sensor-02", "psk-beta-002")

        assert r1.device_id != r2.device_id

    def test_register_records_device_info(self, make_service):
        service = make_service()
        now = datetime(2025, 1, 15, 10, 30, 0)
        result = service.register_device("sensor-01", "psk-alpha-001", registered_at=now)

        device = service.get_device(result.device_id)
        assert device.device_identifier == "sensor-01"
        assert device.registered_at == now
        assert device.status == DeviceStatus.REGISTERED

    def test_register_custom_time(self, make_service):
        service = make_service()
        custom_time = datetime(2024, 6, 1, 0, 0, 0)
        result = service.register_device("sensor-01", "psk-alpha-001", registered_at=custom_time)

        assert result.registered_at == custom_time


class TestCSRSubmission:
    def test_submit_csr_and_issue_certificate(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        csr = CSR(device_id=reg.device_id, public_key_info="rsa-2048-pubkey-abc")
        result = service.submit_csr(csr)

        assert isinstance(result, CertificateIssuanceResult)
        assert result.serial_number.startswith("SN-")
        assert result.device_id == reg.device_id
        assert result.issuer == "TestCA"
        assert result.subject == reg.device_id
        assert result.public_key_info == "rsa-2048-pubkey-abc"
        assert isinstance(result.not_before, datetime)
        assert isinstance(result.not_after, datetime)
        assert result.not_after > result.not_before

    def test_csr_uses_configured_ca_issuer(self, make_service):
        service = make_service(ca_issuer="MyCustomCA")
        reg = service.register_device("sensor-01", "psk-alpha-001")

        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        assert result.issuer == "MyCustomCA"

    def test_csr_certificate_validity_period(self, make_service):
        service = make_service(cert_validity_days=90)
        reg = service.register_device("sensor-01", "psk-alpha-001")

        now = datetime(2025, 1, 1, 0, 0, 0)
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr, now=now)

        assert result.not_before == now
        assert result.not_after == now + timedelta(days=90)

    def test_certificate_stored_in_store(self, make_service):
        store = InMemoryDeviceCertStore()
        service = make_service(store=store)
        reg = service.register_device("sensor-01", "psk-alpha-001")

        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        cert = store.get_certificate(result.serial_number)
        assert cert is not None
        assert cert.serial_number == result.serial_number
        assert cert.status == CertificateStatus.VALID


class TestCertificateRevocation:
    def test_revoke_certificate_by_serial(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        service.revoke_certificate_by_serial(result.serial_number)

        cert = service.query_certificate_by_serial(result.serial_number)
        assert cert.status == CertificateStatus.REVOKED

    def test_revoke_certificates_by_device(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        csr1 = CSR(device_id=reg.device_id, public_key_info="pubkey1")
        csr2 = CSR(device_id=reg.device_id, public_key_info="pubkey2")
        r1 = service.submit_csr(csr1)
        r2 = service.submit_csr(csr2)

        service.revoke_certificates_by_device(reg.device_id)

        c1 = service.query_certificate_by_serial(r1.serial_number)
        c2 = service.query_certificate_by_serial(r2.serial_number)
        assert c1.status == CertificateStatus.REVOKED
        assert c2.status == CertificateStatus.REVOKED

        device = service.get_device(reg.device_id)
        assert device.status == DeviceStatus.REVOKED

    def test_revoke_already_revoked_certificate_is_idempotent(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        service.revoke_certificate_by_serial(result.serial_number)
        service.revoke_certificate_by_serial(result.serial_number)

        cert = service.query_certificate_by_serial(result.serial_number)
        assert cert.status == CertificateStatus.REVOKED


class TestCertificateQuery:
    def test_query_certificates_by_device(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        csr1 = CSR(device_id=reg.device_id, public_key_info="pubkey1")
        csr2 = CSR(device_id=reg.device_id, public_key_info="pubkey2")
        service.submit_csr(csr1)
        service.submit_csr(csr2)

        certs = service.query_certificates_by_device(reg.device_id)
        assert len(certs) == 2

    def test_query_certificates_includes_revoked(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        csr1 = CSR(device_id=reg.device_id, public_key_info="pubkey1")
        csr2 = CSR(device_id=reg.device_id, public_key_info="pubkey2")
        r1 = service.submit_csr(csr1)
        r2 = service.submit_csr(csr2)

        service.revoke_certificate_by_serial(r1.serial_number)

        certs = service.query_certificates_by_device(reg.device_id)
        assert len(certs) == 2

        revoked = [c for c in certs if c.status == CertificateStatus.REVOKED]
        valid = [c for c in certs if c.status == CertificateStatus.VALID]
        assert len(revoked) == 1
        assert len(valid) == 1

    def test_query_certificate_by_serial(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        cert = service.query_certificate_by_serial(result.serial_number)
        assert cert.serial_number == result.serial_number
        assert cert.device_id == reg.device_id
        assert cert.issuer == "TestCA"
        assert cert.subject == reg.device_id
        assert cert.public_key_info == "pubkey"

    def test_query_revoked_certificate_returns_revoked_status(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        service.revoke_certificate_by_serial(result.serial_number)

        cert = service.query_certificate_by_serial(result.serial_number)
        assert cert.status == CertificateStatus.REVOKED


class TestBoundaryConditions:
    def test_revoked_device_cannot_submit_csr(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        service.revoke_certificates_by_device(reg.device_id)

        csr = CSR(device_id=reg.device_id, public_key_info="pubkey-new")
        with pytest.raises(DeviceRevokedError):
            service.submit_csr(csr)

    def test_certificate_validity_boundary_at_not_after(self, make_service):
        service = make_service(cert_validity_days=1)
        reg = service.register_device("sensor-01", "psk-alpha-001")

        now = datetime(2025, 1, 1, 0, 0, 0)
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr, now=now)

        cert_before = service.query_certificate_by_serial(
            result.serial_number, now=datetime(2025, 1, 1, 23, 59, 59)
        )
        assert cert_before.status == CertificateStatus.VALID

        cert_after = service.query_certificate_by_serial(
            result.serial_number, now=datetime(2025, 1, 2, 0, 0, 1)
        )
        assert cert_after.status == CertificateStatus.REVOKED

    def test_certificate_validity_model_boundary(self, make_service):
        service = make_service(cert_validity_days=1)
        reg = service.register_device("sensor-01", "psk-alpha-001")

        now = datetime(2025, 1, 1, 0, 0, 0)
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr, now=now)

        cert_raw = service.query_certificate_by_serial(result.serial_number)
        assert cert_raw.not_before == datetime(2025, 1, 1, 0, 0, 0)
        assert cert_raw.not_after == datetime(2025, 1, 2, 0, 0, 0)

        assert cert_raw.is_expired(now=datetime(2025, 1, 1, 23, 59, 59)) is False
        assert cert_raw.is_expired(now=datetime(2025, 1, 2, 0, 0, 1)) is True

    def test_certificate_validity_minimum_one_day(self, make_service):
        service = make_service(cert_validity_days=1)
        reg = service.register_device("sensor-01", "psk-alpha-001")

        now = datetime(2025, 6, 1, 12, 0, 0)
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr, now=now)

        assert result.not_after - result.not_before == timedelta(days=1)

    def test_same_device_multiple_csrs_issued_multiple_certificates(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        results = []
        for i in range(5):
            csr = CSR(device_id=reg.device_id, public_key_info=f"pubkey-{i}")
            result = service.submit_csr(csr)
            results.append(result)

        assert len(results) == 5
        serial_numbers = [r.serial_number for r in results]
        assert len(set(serial_numbers)) == 5

        certs = service.query_certificates_by_device(reg.device_id)
        assert len(certs) == 5

    def test_revoked_device_revokes_all_existing_certificates(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        for i in range(3):
            csr = CSR(device_id=reg.device_id, public_key_info=f"pubkey-{i}")
            service.submit_csr(csr)

        service.revoke_certificates_by_device(reg.device_id)

        certs = service.query_certificates_by_device(reg.device_id)
        assert all(c.status == CertificateStatus.REVOKED for c in certs)

    def test_expired_certificate_shows_revoked_status(self, make_service):
        service = make_service(cert_validity_days=1)
        reg = service.register_device("sensor-01", "psk-alpha-001")

        issue_time = datetime(2025, 1, 1, 0, 0, 0)
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr, now=issue_time)

        query_time = datetime(2026, 1, 1, 0, 0, 0)
        cert = service.query_certificate_by_serial(result.serial_number, now=query_time)
        assert cert.status == CertificateStatus.REVOKED

    def test_expired_certificate_in_by_device_query(self, make_service):
        service = make_service(cert_validity_days=1)
        reg = service.register_device("sensor-01", "psk-alpha-001")

        issue_time = datetime(2025, 1, 1, 0, 0, 0)
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr, now=issue_time)

        query_time = datetime(2025, 1, 3, 0, 0, 0)
        certs = service.query_certificates_by_device(reg.device_id, now=query_time)
        assert len(certs) == 1
        assert certs[0].status == CertificateStatus.REVOKED
        assert certs[0].serial_number == result.serial_number


class TestExceptionBranches:
    def test_wrong_psk_rejected(self, make_service):
        service = make_service()

        with pytest.raises(InvalidPSKError):
            service.register_device("sensor-01", "wrong-psk")

    def test_unregistered_device_csr_rejected(self, make_service):
        service = make_service()

        csr = CSR(device_id="dev-nonexistent", public_key_info="pubkey")
        with pytest.raises(DeviceNotFoundError):
            service.submit_csr(csr)

    def test_duplicate_device_identifier_rejected(self, make_service):
        service = make_service()
        service.register_device("sensor-01", "psk-alpha-001")

        with pytest.raises(DuplicateDeviceError):
            service.register_device("sensor-01", "psk-beta-002")

    def test_revoke_nonexistent_serial_raises(self, make_service):
        service = make_service()

        with pytest.raises(CertificateNotFoundError):
            service.revoke_certificate_by_serial("SN-NONEXISTENT")

    def test_csr_device_id_not_found_rejected(self, make_service):
        service = make_service()

        csr = CSR(device_id="dev-doesnotexist", public_key_info="pubkey")
        with pytest.raises(DeviceNotFoundError):
            service.submit_csr(csr)

    def test_query_certificates_nonexistent_device(self, make_service):
        service = make_service()

        with pytest.raises(DeviceNotFoundError):
            service.query_certificates_by_device("dev-nonexistent")

    def test_query_certificate_nonexistent_serial(self, make_service):
        service = make_service()

        with pytest.raises(CertificateNotFoundError):
            service.query_certificate_by_serial("SN-NONEXISTENT")

    def test_revoke_by_nonexistent_device_raises(self, make_service):
        service = make_service()

        with pytest.raises(DeviceNotFoundError):
            service.revoke_certificates_by_device("dev-nonexistent")

    def test_empty_psk_list_raises(self):
        with pytest.raises(ValueError, match="PSK list must not be empty"):
            DeviceCertService(psk_list=set())

    def test_zero_validity_days_raises(self):
        with pytest.raises(ValueError, match="validity days must be at least 1"):
            DeviceCertService(psk_list=VALID_PSK_LIST, cert_validity_days=0)

    def test_negative_validity_days_raises(self):
        with pytest.raises(ValueError, match="validity days must be at least 1"):
            DeviceCertService(psk_list=VALID_PSK_LIST, cert_validity_days=-1)

    def test_get_device_not_found(self, make_service):
        service = make_service()

        with pytest.raises(DeviceNotFoundError):
            service.get_device("dev-nonexistent")

    def test_revoked_device_csr_not_device_not_found(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        service.revoke_certificates_by_device(reg.device_id)

        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        with pytest.raises(DeviceRevokedError):
            service.submit_csr(csr)


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_device_cert_error(self):
        from solocoder_py.device_cert import DeviceCertError

        assert issubclass(InvalidPSKError, DeviceCertError)
        assert issubclass(DuplicateDeviceError, DeviceCertError)
        assert issubclass(DeviceNotFoundError, DeviceCertError)
        assert issubclass(DeviceNotRegisteredError, DeviceCertError)
        assert issubclass(DeviceRevokedError, DeviceCertError)
        assert issubclass(CertificateNotFoundError, DeviceCertError)


class TestInMemoryStore:
    def test_store_and_retrieve_device(self, make_store):
        store = make_store()
        device = DeviceRecord(
            device_id="dev-001",
            device_identifier="sensor-01",
            registered_at=datetime.now(),
            status=DeviceStatus.REGISTERED,
        )
        store.store_device(device)

        retrieved = store.get_device("dev-001")
        assert retrieved is not None
        assert retrieved.device_id == "dev-001"

    def test_get_nonexistent_device(self, make_store):
        store = make_store()
        assert store.get_device("dev-999") is None

    def test_has_identifier(self, make_store):
        store = make_store()
        device = DeviceRecord(
            device_id="dev-001",
            device_identifier="sensor-01",
            registered_at=datetime.now(),
        )
        store.store_device(device)

        assert store.has_identifier("sensor-01") is True
        assert store.has_identifier("sensor-02") is False

    def test_next_serial_increments(self, make_store):
        store = make_store()

        s1 = store.next_serial()
        s2 = store.next_serial()
        s3 = store.next_serial()

        assert s1 == "SN-00000001"
        assert s2 == "SN-00000002"
        assert s3 == "SN-00000003"

    def test_clear_store(self, make_store, make_service):
        store = make_store()
        service = make_service(store=store)

        service.register_device("sensor-01", "psk-alpha-001")
        assert len(store) == 1

        store.clear()
        assert len(store) == 0

    def test_store_len(self, make_store, make_service):
        store = make_store()
        service = make_service(store=store)

        assert len(store) == 0
        service.register_device("sensor-01", "psk-alpha-001")
        assert len(store) == 1
        service.register_device("sensor-02", "psk-beta-002")
        assert len(store) == 2


class TestImmutability:
    def test_get_device_returns_copy(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        device1 = service.get_device(reg.device_id)
        device2 = service.get_device(reg.device_id)

        assert device1.device_id == device2.device_id
        assert device1 is not device2

    def test_modifying_returned_device_does_not_affect_internal_state(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")

        device_copy = service.get_device(reg.device_id)
        device_copy.status = DeviceStatus.REVOKED

        device_again = service.get_device(reg.device_id)
        assert device_again.status == DeviceStatus.REGISTERED

    def test_query_certificate_by_serial_returns_copy(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        cert1 = service.query_certificate_by_serial(result.serial_number)
        cert2 = service.query_certificate_by_serial(result.serial_number)

        assert cert1 is not cert2

    def test_query_certificates_by_device_returns_copies(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        service.submit_csr(csr)

        certs1 = service.query_certificates_by_device(reg.device_id)
        certs2 = service.query_certificates_by_device(reg.device_id)

        assert certs1[0] is not certs2[0]

    def test_modifying_returned_certificate_does_not_affect_internal_state(self, make_service):
        service = make_service()
        reg = service.register_device("sensor-01", "psk-alpha-001")
        csr = CSR(device_id=reg.device_id, public_key_info="pubkey")
        result = service.submit_csr(csr)

        cert_copy = service.query_certificate_by_serial(result.serial_number)
        cert_copy.public_key_info = "tampered-key"
        cert_copy.serial_number = "SN-TAMPERED"

        cert_again = service.query_certificate_by_serial(result.serial_number)
        assert cert_again.public_key_info == "pubkey"
        assert cert_again.serial_number == result.serial_number


class TestDefaults:
    def test_default_ca_issuer(self):
        assert DEFAULT_CA_ISSUER == "SoloCoder-CA"

    def test_default_cert_validity_days(self):
        assert DEFAULT_CERT_VALIDITY_DAYS == 365
