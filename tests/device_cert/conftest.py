import pytest

from solocoder_py.device_cert import (
    DeviceCertService,
    InMemoryDeviceCertStore,
)

VALID_PSK_LIST = {"psk-alpha-001", "psk-beta-002", "psk-gamma-003"}


@pytest.fixture
def make_store():
    def _make_store() -> InMemoryDeviceCertStore:
        return InMemoryDeviceCertStore()
    return _make_store


@pytest.fixture
def make_service():
    def _make_service(
        psk_list: set[str] | None = None,
        ca_issuer: str = "TestCA",
        cert_validity_days: int = 365,
        store: InMemoryDeviceCertStore | None = None,
    ) -> DeviceCertService:
        return DeviceCertService(
            psk_list=psk_list if psk_list is not None else set(VALID_PSK_LIST),
            ca_issuer=ca_issuer,
            cert_validity_days=cert_validity_days,
            store=store if store is not None else InMemoryDeviceCertStore(),
        )
    return _make_service
