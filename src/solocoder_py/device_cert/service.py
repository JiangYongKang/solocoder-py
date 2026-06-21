from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from .exceptions import (
    DeviceNotFoundError,
    DeviceNotRegisteredError,
    DuplicateDeviceError,
    InvalidPSKError,
    CertificateNotFoundError,
)
from .models import (
    CSR,
    Certificate,
    CertificateIssuanceResult,
    CertificateStatus,
    DeviceRecord,
    DeviceStatus,
    RegistrationResult,
)
from .store import InMemoryDeviceCertStore

DEFAULT_CERT_VALIDITY_DAYS = 365
DEFAULT_CA_ISSUER = "SoloCoder-CA"


class DeviceCertService:
    def __init__(
        self,
        psk_list: set[str],
        ca_issuer: str = DEFAULT_CA_ISSUER,
        cert_validity_days: int = DEFAULT_CERT_VALIDITY_DAYS,
        store: Optional[InMemoryDeviceCertStore] = None,
    ) -> None:
        if not psk_list:
            raise ValueError("PSK list must not be empty")
        if cert_validity_days < 1:
            raise ValueError("Certificate validity days must be at least 1")

        self._psk_list = psk_list
        self._ca_issuer = ca_issuer
        self._cert_validity_days = cert_validity_days
        self._store = store if store is not None else InMemoryDeviceCertStore()

    @property
    def ca_issuer(self) -> str:
        return self._ca_issuer

    @property
    def cert_validity_days(self) -> int:
        return self._cert_validity_days

    def register_device(
        self,
        device_identifier: str,
        psk: str,
        registered_at: Optional[datetime] = None,
    ) -> RegistrationResult:
        if psk not in self._psk_list:
            raise InvalidPSKError(f"Invalid PSK for device identifier: {device_identifier}")

        if self._store.has_identifier(device_identifier):
            raise DuplicateDeviceError(f"Device identifier already registered: {device_identifier}")

        device_id = f"dev-{uuid.uuid4().hex[:16]}"
        now = registered_at if registered_at is not None else datetime.now()

        device = DeviceRecord(
            device_id=device_id,
            device_identifier=device_identifier,
            registered_at=now,
            status=DeviceStatus.REGISTERED,
        )
        self._store.store_device(device)

        return RegistrationResult(
            device_id=device_id,
            device_identifier=device_identifier,
            registered_at=now,
        )

    def submit_csr(
        self,
        csr: CSR,
        now: Optional[datetime] = None,
    ) -> CertificateIssuanceResult:
        device = self._store.get_device(csr.device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device not found: {csr.device_id}")

        if device.status != DeviceStatus.REGISTERED:
            raise DeviceNotRegisteredError(
                f"Device {csr.device_id} is not in registered state (current: {device.status.value})"
            )

        current_time = now if now is not None else datetime.now()
        not_before = current_time
        not_after = current_time + timedelta(days=self._cert_validity_days)

        serial_number = self._store.next_serial()

        cert = Certificate(
            serial_number=serial_number,
            device_id=csr.device_id,
            issuer=self._ca_issuer,
            subject=csr.device_id,
            public_key_info=csr.public_key_info,
            not_before=not_before,
            not_after=not_after,
            status=CertificateStatus.VALID,
        )
        self._store.store_certificate(cert)

        return CertificateIssuanceResult(
            serial_number=serial_number,
            device_id=csr.device_id,
            issuer=self._ca_issuer,
            subject=csr.device_id,
            public_key_info=csr.public_key_info,
            not_before=not_before,
            not_after=not_after,
        )

    def revoke_certificate_by_serial(self, serial_number: str) -> None:
        cert = self._store.get_certificate(serial_number)
        if cert is None:
            raise CertificateNotFoundError(f"Certificate not found: {serial_number}")
        cert.status = CertificateStatus.REVOKED

    def revoke_certificates_by_device(self, device_id: str) -> None:
        device = self._store.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device not found: {device_id}")

        device.status = DeviceStatus.REVOKED
        certs = self._store.get_certificates_by_device(device_id)
        for cert in certs:
            cert.status = CertificateStatus.REVOKED

    def query_certificates_by_device(self, device_id: str) -> list[Certificate]:
        device = self._store.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device not found: {device_id}")
        return list(self._store.get_certificates_by_device(device_id))

    def query_certificate_by_serial(self, serial_number: str) -> Certificate:
        cert = self._store.get_certificate(serial_number)
        if cert is None:
            raise CertificateNotFoundError(f"Certificate not found: {serial_number}")
        return cert

    def get_device(self, device_id: str) -> DeviceRecord:
        device = self._store.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(f"Device not found: {device_id}")
        return device
