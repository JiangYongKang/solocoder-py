from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ReconciliationError(Exception):
    pass


class TransactionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    REFUNDED = "refunded"


class TransactionSide(str, Enum):
    INTERNAL = "internal"
    CHANNEL = "channel"


class MatchType(str, Enum):
    EXACT = "exact"
    TOLERANCE = "tolerance"
    FALLBACK = "fallback"


class DiscrepancyType(str, Enum):
    CHANNEL_MISSING = "channel_missing"
    INTERNAL_MISSING = "internal_missing"
    AMOUNT_MISMATCH = "amount_mismatch"
    STATUS_MISMATCH = "status_mismatch"


@dataclass(frozen=True)
class ToleranceConfig:
    absolute_tolerance: float = 0.01
    relative_tolerance: float = 0.0001

    def is_within_tolerance(self, internal_amount: float, channel_amount: float) -> bool:
        abs_diff = abs(internal_amount - channel_amount)
        if abs_diff <= self.absolute_tolerance:
            return True
        if internal_amount == 0 and channel_amount == 0:
            return True
        base = max(abs(internal_amount), abs(channel_amount))
        if base == 0:
            return abs_diff <= self.absolute_tolerance
        return abs_diff / base <= self.relative_tolerance

    def diff_amount(self, internal_amount: float, channel_amount: float) -> float:
        return internal_amount - channel_amount


@dataclass
class Transaction:
    txn_id: Optional[str]
    amount: float
    txn_time: datetime
    status: TransactionStatus
    side: TransactionSide
    raw_data: Dict = field(default_factory=dict)
    order_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ReconciliationError("Transaction amount cannot be negative")

    @property
    def has_txn_id(self) -> bool:
        return self.txn_id is not None and self.txn_id != ""


@dataclass
class MatchedPair:
    internal_txn: Transaction
    channel_txn: Transaction
    match_type: MatchType
    diff_amount: float = 0.0
    matched_at: datetime = field(default_factory=datetime.now)
    write_off: bool = False


@dataclass
class Discrepancy:
    discrepancy_id: str
    type: DiscrepancyType
    internal_txn: Optional[Transaction] = None
    channel_txn: Optional[Transaction] = None
    detail: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        dtype: DiscrepancyType,
        internal_txn: Optional[Transaction] = None,
        channel_txn: Optional[Transaction] = None,
        detail: str = "",
    ) -> "Discrepancy":
        return cls(
            discrepancy_id=str(uuid.uuid4()),
            type=dtype,
            internal_txn=internal_txn,
            channel_txn=channel_txn,
            detail=detail,
        )

    @property
    def amount(self) -> float:
        if self.internal_txn is not None:
            return self.internal_txn.amount
        if self.channel_txn is not None:
            return self.channel_txn.amount
        return 0.0


@dataclass
class ReconciliationReport:
    batch_id: str
    start_time: datetime
    end_time: datetime
    internal_total_count: int
    internal_total_amount: float
    channel_total_count: int
    channel_total_amount: float
    matched_count: int
    matched_amount: float
    tolerance_write_off_count: int
    tolerance_write_off_diff_amount: float
    internal_discrepancies: Dict[DiscrepancyType, List[Discrepancy]]
    channel_discrepancies: Dict[DiscrepancyType, List[Discrepancy]]
    matched_pairs: List[MatchedPair] = field(default_factory=list)

    @property
    def internal_discrepancy_total_count(self) -> int:
        return sum(len(v) for v in self.internal_discrepancies.values())

    @property
    def internal_discrepancy_total_amount(self) -> float:
        return sum(d.amount for lst in self.internal_discrepancies.values() for d in lst)

    @property
    def channel_discrepancy_total_count(self) -> int:
        return sum(len(v) for v in self.channel_discrepancies.values())

    @property
    def channel_discrepancy_total_amount(self) -> float:
        return sum(d.amount for lst in self.channel_discrepancies.values() for d in lst)

    def summary(self) -> Dict:
        return {
            "batch_id": self.batch_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "internal_total": {
                "count": self.internal_total_count,
                "amount": self.internal_total_amount,
            },
            "channel_total": {
                "count": self.channel_total_count,
                "amount": self.channel_total_amount,
            },
            "matched": {
                "count": self.matched_count,
                "amount": self.matched_amount,
            },
            "tolerance_write_off": {
                "count": self.tolerance_write_off_count,
                "diff_amount": self.tolerance_write_off_diff_amount,
            },
            "internal_discrepancies": {
                dtype.value: {"count": len(lst), "amount": sum(d.amount for d in lst)}
                for dtype, lst in self.internal_discrepancies.items()
            },
            "channel_discrepancies": {
                dtype.value: {"count": len(lst), "amount": sum(d.amount for d in lst)}
                for dtype, lst in self.channel_discrepancies.items()
            },
        }
