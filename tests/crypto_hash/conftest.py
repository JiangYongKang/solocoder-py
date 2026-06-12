import pytest

from solocoder_py.crypto_hash import (
    CryptoHashService,
    AlgorithmVersion,
    InMemoryHashStore,
)


@pytest.fixture
def make_service():
    def _make_service(
        algorithm: AlgorithmVersion = AlgorithmVersion.BCRYPT_V3,
        salt_length: int = 16,
        iterations: int = 10,
    ) -> CryptoHashService:
        return CryptoHashService(
            default_algorithm=algorithm,
            salt_length=salt_length,
            iterations=iterations,
            store=InMemoryHashStore(),
        )
    return _make_service


@pytest.fixture
def make_store():
    def _make_store() -> InMemoryHashStore:
        return InMemoryHashStore()
    return _make_store
