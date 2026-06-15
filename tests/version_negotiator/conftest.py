from __future__ import annotations

import pytest

from solocoder_py.version_negotiator import (
    VersionNegotiator,
    VersionNegotiatorConfig,
    VersionedRequest,
    VersionedResponse,
)


class ManualClock:
    def __init__(self, start_time: float = 1_700_000_000.0) -> None:
        self._time = start_time

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


def _make_handler(version: str, return_body=None):
    body = return_body or {"version": version, "message": f"Hello from {version}"}

    def handler(request: VersionedRequest) -> VersionedResponse:
        return VersionedResponse(status_code=200, body=body)

    return handler


@pytest.fixture
def make_handler():
    return _make_handler


@pytest.fixture
def base_timestamp() -> float:
    return 1_700_000_000.0


@pytest.fixture
def manual_clock(base_timestamp: float) -> ManualClock:
    return ManualClock(start_time=base_timestamp)


@pytest.fixture
def default_config() -> VersionNegotiatorConfig:
    return VersionNegotiatorConfig(
        default_version=None,
        accept_version_header="Accept-Version",
        deprecation_header="Deprecation",
        sunset_header="Sunset",
        deprecation_link_header="Link",
        deprecation_link=None,
        strict_version_matching=False,
        require_version_header=False,
    )


@pytest.fixture
def basic_negotiator(
    default_config: VersionNegotiatorConfig, manual_clock: ManualClock
) -> VersionNegotiator:
    negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
    negotiator.register("v1", _make_handler("v1"))
    negotiator.register("v2", _make_handler("v2"))
    negotiator.set_default_version("v2")
    return negotiator


@pytest.fixture
def negotiator_with_semver(
    default_config: VersionNegotiatorConfig, manual_clock: ManualClock
) -> VersionNegotiator:
    negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
    negotiator.register("v1.0", _make_handler("v1.0"))
    negotiator.register("v1.5", _make_handler("v1.5"))
    negotiator.register("v2.0", _make_handler("v2.0"))
    negotiator.register("v2.1", _make_handler("v2.1"))
    negotiator.set_default_version("v2.1")
    return negotiator


@pytest.fixture
def negotiator_with_date_versions(
    default_config: VersionNegotiatorConfig, manual_clock: ManualClock
) -> VersionNegotiator:
    negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
    negotiator.register("v2024-01", _make_handler("v2024-01"))
    negotiator.register("v2024-06", _make_handler("v2024-06"))
    negotiator.register("v2024-06-15", _make_handler("v2024-06-15"))
    negotiator.set_default_version("v2024-06-15")
    return negotiator


@pytest.fixture
def negotiator_with_deprecated(
    default_config: VersionNegotiatorConfig,
    manual_clock: ManualClock,
    base_timestamp: float,
) -> VersionNegotiator:
    negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
    sunset_at = base_timestamp + 1_000_000
    negotiator.register(
        "v1",
        _make_handler("v1"),
        is_deprecated=True,
        sunset_at=sunset_at,
        deprecated_at=base_timestamp,
        deprecation_message="v1 is deprecated, please use v2",
    )
    negotiator.register("v2", _make_handler("v2"))
    negotiator.set_default_version("v2")
    return negotiator


@pytest.fixture
def strict_negotiator(
    manual_clock: ManualClock,
) -> VersionNegotiator:
    config = VersionNegotiatorConfig(
        strict_version_matching=True,
        default_version="v2",
    )
    negotiator = VersionNegotiator(config=config, clock=manual_clock)
    negotiator.register("v1.0", _make_handler("v1.0"))
    negotiator.register("v2.0", _make_handler("v2.0"))
    return negotiator


__all__ = [
    "ManualClock",
    "make_handler",
]
