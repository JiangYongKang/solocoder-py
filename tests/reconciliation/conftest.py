from datetime import datetime, timedelta

import pytest

from solocoder_py.reconciliation import (
    ReconciliationEngine,
    ToleranceConfig,
    TransactionSide,
    TransactionStatus,
)


@pytest.fixture
def base_time():
    return datetime(2024, 1, 1, 10, 0, 0)


@pytest.fixture
def default_engine():
    return ReconciliationEngine()


@pytest.fixture
def strict_engine():
    return ReconciliationEngine(
        tolerance=ToleranceConfig(absolute_tolerance=0.0, relative_tolerance=0.0)
    )


@pytest.fixture
def lenient_engine():
    return ReconciliationEngine(
        tolerance=ToleranceConfig(absolute_tolerance=1.0, relative_tolerance=0.001)
    )


def make_internal_record(txn_id, amount, txn_time=None, status="success", **extra):
    rec = {
        "txn_id": txn_id,
        "amount": amount,
        "txn_time": txn_time or datetime(2024, 1, 1, 10, 0, 0),
        "status": status,
    }
    rec.update(extra)
    return rec


def make_channel_record(txn_id, amount, txn_time=None, status="success", **extra):
    rec = {
        "trade_no": txn_id,
        "amount": amount,
        "trade_time": txn_time or datetime(2024, 1, 1, 10, 0, 0),
        "status": status,
    }
    rec.update(extra)
    return rec
