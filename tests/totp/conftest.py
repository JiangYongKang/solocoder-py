import pytest

from solocoder_py.totp import (
    TotpService,
    InMemoryTotpStore,
)


@pytest.fixture
def make_service():
    def _make_service(
        issuer: str = "TestIssuer",
        drift_windows: int = 1,
        secret_bytes: int = 20,
    ) -> TotpService:
        return TotpService(
            issuer=issuer,
            drift_windows=drift_windows,
            secret_bytes=secret_bytes,
            store=InMemoryTotpStore(),
        )
    return _make_service


@pytest.fixture
def make_store():
    def _make_store() -> InMemoryTotpStore:
        return InMemoryTotpStore()
    return _make_store
