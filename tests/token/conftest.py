from datetime import timedelta

import pytest

from solocoder_py.token import TokenRepository, TokenService


@pytest.fixture
def repo() -> TokenRepository:
    return TokenRepository()


@pytest.fixture
def service(repo: TokenRepository) -> TokenService:
    return TokenService(
        repository=repo,
        access_token_ttl=timedelta(minutes=15),
        refresh_token_ttl=timedelta(days=7),
    )


@pytest.fixture
def short_ttl_service(repo: TokenRepository) -> TokenService:
    return TokenService(
        repository=repo,
        access_token_ttl=timedelta(milliseconds=50),
        refresh_token_ttl=timedelta(milliseconds=50),
    )
