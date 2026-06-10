from __future__ import annotations

import pytest

from solocoder_py.abac import (
    ABACEngine,
    AttributeCondition,
    AttributeCategory,
    ComparisonOperator,
    ConditionExpression,
    ConflictResolutionStrategy,
    LogicalOperator,
    Policy,
    PolicyEffect,
    RequestContext,
)


@pytest.fixture
def engine():
    return ABACEngine()


@pytest.fixture
def permit_overrides_engine():
    return ABACEngine(conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES)


@pytest.fixture
def highest_priority_engine():
    return ABACEngine(conflict_strategy=ConflictResolutionStrategy.HIGHEST_PRIORITY)


@pytest.fixture
def admin_context():
    return RequestContext(
        subject={"role": "admin", "user_id": "u1", "department": "IT"},
        resource={"type": "document", "owner": "u1", "sensitivity": "high"},
        environment={"time": "09:00", "ip": "192.168.1.1"},
    )


@pytest.fixture
def user_context():
    return RequestContext(
        subject={"role": "user", "user_id": "u2", "department": "Sales"},
        resource={"type": "document", "owner": "u1", "sensitivity": "low"},
        environment={"time": "22:00", "ip": "10.0.0.1"},
    )


@pytest.fixture
def empty_context():
    return RequestContext()
