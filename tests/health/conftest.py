from __future__ import annotations

from typing import Callable, Tuple

import pytest

from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
)


def healthy_check() -> Tuple[bool, None]:
    return True, None


def unhealthy_check() -> Tuple[bool, str]:
    return False, "Check failed"


def make_aggregator() -> HealthCheckAggregator:
    return HealthCheckAggregator()


def make_component_config(
    *,
    component_id: str,
    is_core: bool = False,
    dependencies: list[str] | None = None,
    readiness_check: Callable[[], Tuple[bool, str | None]] | None = None,
    liveness_check: Callable[[], Tuple[bool, str | None]] | None = None,
) -> ComponentConfig:
    deps = dependencies or []
    rc = readiness_check if readiness_check is not None else healthy_check
    lc = liveness_check if liveness_check is not None else healthy_check
    return ComponentConfig(
        component_id=component_id,
        is_core=is_core,
        dependencies=deps,
        readiness_check=rc,
        liveness_check=lc,
    )


@pytest.fixture
def aggregator() -> HealthCheckAggregator:
    return make_aggregator()
