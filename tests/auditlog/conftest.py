import pytest

from solocoder_py.auditlog import AuditLogStore, AuditLogValidator
from solocoder_py.seat.clock import ManualClock


@pytest.fixture
def manual_clock():
    return ManualClock(start_time=1_700_000_000.0)


@pytest.fixture
def store(manual_clock):
    return AuditLogStore(clock=manual_clock)


@pytest.fixture
def validator():
    return AuditLogValidator()
