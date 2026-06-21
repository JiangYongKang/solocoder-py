from __future__ import annotations


class DeviceCertError(Exception):
    pass


class InvalidPSKError(DeviceCertError):
    pass


class DuplicateDeviceError(DeviceCertError):
    pass


class DeviceNotFoundError(DeviceCertError):
    pass


class DeviceNotRegisteredError(DeviceCertError):
    pass


class CertificateNotFoundError(DeviceCertError):
    pass
