from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DeviceStatus(str, Enum):
    REGISTERED = "registered"
    REVOKED = "revoked"


class CertificateStatus(str, Enum):
    VALID = "valid"
    REVOKED = "revoked"


@dataclass
class DeviceRecord:
    device_id: str
    device_identifier: str
    registered_at: datetime
    status: DeviceStatus = DeviceStatus.REGISTERED


@dataclass
class Certificate:
    serial_number: str
    device_id: str
    issuer: str
    subject: str
    public_key_info: str
    not_before: datetime
    not_after: datetime
    status: CertificateStatus = CertificateStatus.VALID

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if now is None:
            now = datetime.now()
        return now > self.not_after


@dataclass
class CSR:
    device_id: str
    public_key_info: str


@dataclass
class RegistrationResult:
    device_id: str
    device_identifier: str
    registered_at: datetime


@dataclass
class CertificateIssuanceResult:
    serial_number: str
    device_id: str
    issuer: str
    subject: str
    public_key_info: str
    not_before: datetime
    not_after: datetime
