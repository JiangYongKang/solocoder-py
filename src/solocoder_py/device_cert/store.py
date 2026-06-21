from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import Certificate, DeviceRecord


@dataclass
class InMemoryDeviceCertStore:
    devices: dict[str, DeviceRecord] = field(default_factory=dict)
    certificates: dict[str, Certificate] = field(default_factory=dict)
    device_certificates: dict[str, list[str]] = field(default_factory=dict)
    identifier_index: dict[str, str] = field(default_factory=dict)
    _serial_counter: int = field(default=0)

    def store_device(self, device: DeviceRecord) -> None:
        self.devices[device.device_id] = device
        self.identifier_index[device.device_identifier] = device.device_id

    def get_device(self, device_id: str) -> Optional[DeviceRecord]:
        return self.devices.get(device_id)

    def has_identifier(self, device_identifier: str) -> bool:
        return device_identifier in self.identifier_index

    def store_certificate(self, cert: Certificate) -> None:
        self.certificates[cert.serial_number] = cert
        if cert.device_id not in self.device_certificates:
            self.device_certificates[cert.device_id] = []
        self.device_certificates[cert.device_id].append(cert.serial_number)

    def get_certificate(self, serial_number: str) -> Optional[Certificate]:
        return self.certificates.get(serial_number)

    def get_certificates_by_device(self, device_id: str) -> list[Certificate]:
        serial_numbers = self.device_certificates.get(device_id, [])
        certs = []
        for sn in serial_numbers:
            cert = self.certificates.get(sn)
            if cert is not None:
                certs.append(cert)
        return certs

    def next_serial(self) -> str:
        self._serial_counter += 1
        return f"SN-{self._serial_counter:08d}"

    def clear(self) -> None:
        self.devices.clear()
        self.certificates.clear()
        self.device_certificates.clear()
        self.identifier_index.clear()
        self._serial_counter = 0

    def __len__(self) -> int:
        return len(self.devices)
