from __future__ import annotations

import pytest

from solocoder_py.credential import (
    CredentialRotator,
    ManualClock,
    MemoryWriteTarget,
    RotationConfig,
    RotationStore,
    TrafficRouter,
)


@pytest.fixture
def manual_clock() -> ManualClock:
    return ManualClock(_current_time=1000.0)


@pytest.fixture
def write_target() -> MemoryWriteTarget:
    return MemoryWriteTarget()


@pytest.fixture
def router() -> TrafficRouter:
    return TrafficRouter()


@pytest.fixture
def store() -> RotationStore:
    return RotationStore()


@pytest.fixture
def sample_config() -> RotationConfig:
    return RotationConfig(
        credential_name="db-password",
        old_credential="old-secret-123",
        new_credential="new-secret-456",
        dual_write_duration_seconds=300.0,
        traffic_step_percentage=20,
        max_error_rate=0.05,
        consecutive_failure_threshold=5,
        cooldown_seconds=120.0,
        min_requests_for_evaluation=20,
    )


@pytest.fixture
def sample_config_small_steps() -> RotationConfig:
    return RotationConfig(
        credential_name="api-key",
        old_credential="old-key-aaa",
        new_credential="new-key-bbb",
        dual_write_duration_seconds=60.0,
        traffic_step_percentage=10,
        max_error_rate=0.10,
        consecutive_failure_threshold=3,
        cooldown_seconds=60.0,
        min_requests_for_evaluation=10,
    )


@pytest.fixture
def rotator(
    manual_clock: ManualClock,
    write_target: MemoryWriteTarget,
    router: TrafficRouter,
    store: RotationStore,
) -> CredentialRotator:
    return CredentialRotator(
        write_target=write_target,
        clock=manual_clock,
        store=store,
        router=router,
    )


@pytest.fixture
def rotator_with_rotation(
    rotator: CredentialRotator,
    sample_config: RotationConfig,
) -> CredentialRotator:
    rotator.create_rotation(sample_config)
    return rotator
