from __future__ import annotations

import pytest

from solocoder_py.seat.clock import ManualClock
from solocoder_py.jwt import (
    JWTClock,
    JWTConfig,
    JWTService,
    KeyStore,
)


@pytest.fixture
def base_timestamp() -> float:
    return 1718150400.0


@pytest.fixture
def manual_clock(base_timestamp: float) -> ManualClock:
    return ManualClock(start_time=base_timestamp)


@pytest.fixture
def jwt_clock(manual_clock: ManualClock) -> JWTClock:
    return JWTClock.from_clock(manual_clock)


@pytest.fixture
def default_config() -> JWTConfig:
    return JWTConfig(
        issuer="test-issuer",
        audiences=["service-a", "service-b"],
        allowed_algorithms={"HS256", "HS384", "HS512"},
        default_algorithm="HS256",
        default_expire_seconds=3600,
        key_retire_seconds=86400,
        current_service_id="service-a",
        allowed_issuers=["test-issuer"],
    )


@pytest.fixture
def key_store(default_config: JWTConfig, jwt_clock: JWTClock) -> KeyStore:
    ks = KeyStore(default_config, jwt_clock)
    ks.add_key(algorithm="HS256", kid="key-v1")
    return ks


@pytest.fixture
def jwt_service(default_config: JWTConfig, key_store: KeyStore, jwt_clock: JWTClock) -> JWTService:
    return JWTService(default_config, key_store, jwt_clock)
