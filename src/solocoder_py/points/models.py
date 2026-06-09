from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from uuid import uuid4

from .exceptions import FreezeStateError, InvalidAmountError


class FreezeStatus(str, Enum):
    FROZEN = "frozen"
    CONSUMED = "consumed"
    UNFROZEN = "unfrozen"


@dataclass
class PointsBatch:
    batch_id: str
    account_id: str
    total_points: int
    remaining_points: int
    frozen_points: int
    created_at: datetime
    expired_at: datetime

    def __post_init__(self) -> None:
        if not self.batch_id:
            raise ValueError("batch_id cannot be empty")
        if not self.account_id:
            raise ValueError("account_id cannot be empty")
        if self.total_points < 0:
            raise InvalidAmountError("total_points cannot be negative")
        if self.remaining_points < 0:
            raise InvalidAmountError("remaining_points cannot be negative")
        if self.frozen_points < 0:
            raise InvalidAmountError("frozen_points cannot be negative")
        if self.remaining_points + self.frozen_points > self.total_points:
            raise InvalidAmountError(
                "remaining_points + frozen_points cannot exceed total_points"
            )

    @property
    def available_points(self) -> int:
        return self.remaining_points

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        check_time = now if now is not None else datetime.now()
        return check_time >= self.expired_at

    def copy(self) -> "PointsBatch":
        return PointsBatch(
            batch_id=self.batch_id,
            account_id=self.account_id,
            total_points=self.total_points,
            remaining_points=self.remaining_points,
            frozen_points=self.frozen_points,
            created_at=self.created_at,
            expired_at=self.expired_at,
        )


@dataclass
class FrozenRecord:
    freeze_id: str
    account_id: str
    total_amount: int
    status: FreezeStatus
    created_at: datetime
    batch_deductions: Dict[str, int] = field(default_factory=dict)
    consumed_at: Optional[datetime] = None
    unfrozen_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.freeze_id:
            raise ValueError("freeze_id cannot be empty")
        if not self.account_id:
            raise ValueError("account_id cannot be empty")
        if self.total_amount < 0:
            raise InvalidAmountError("total_amount cannot be negative")
        for batch_id, amount in self.batch_deductions.items():
            if amount < 0:
                raise InvalidAmountError(
                    f"batch deduction amount cannot be negative for batch {batch_id}"
                )

    @property
    def is_frozen(self) -> bool:
        return self.status == FreezeStatus.FROZEN

    @property
    def is_consumed(self) -> bool:
        return self.status == FreezeStatus.CONSUMED

    @property
    def is_unfrozen(self) -> bool:
        return self.status == FreezeStatus.UNFROZEN

    def mark_consumed(self) -> None:
        if not self.is_frozen:
            raise FreezeStateError(f"Cannot consume freeze in state {self.status}")
        self.status = FreezeStatus.CONSUMED
        self.consumed_at = datetime.now()

    def mark_unfrozen(self) -> None:
        if not self.is_frozen:
            raise FreezeStateError(f"Cannot unfreeze freeze in state {self.status}")
        self.status = FreezeStatus.UNFROZEN
        self.unfrozen_at = datetime.now()

    def copy(self) -> "FrozenRecord":
        return FrozenRecord(
            freeze_id=self.freeze_id,
            account_id=self.account_id,
            total_amount=self.total_amount,
            status=self.status,
            created_at=self.created_at,
            batch_deductions=dict(self.batch_deductions),
            consumed_at=self.consumed_at,
            unfrozen_at=self.unfrozen_at,
        )


@dataclass
class ExpiredLog:
    log_id: str
    account_id: str
    batch_id: str
    recycled_points: int
    recycled_at: datetime

    def __post_init__(self) -> None:
        if not self.log_id:
            raise ValueError("log_id cannot be empty")
        if not self.account_id:
            raise ValueError("account_id cannot be empty")
        if not self.batch_id:
            raise ValueError("batch_id cannot be empty")
        if self.recycled_points < 0:
            raise InvalidAmountError("recycled_points cannot be negative")

    def copy(self) -> "ExpiredLog":
        return ExpiredLog(
            log_id=self.log_id,
            account_id=self.account_id,
            batch_id=self.batch_id,
            recycled_points=self.recycled_points,
            recycled_at=self.recycled_at,
        )


@dataclass
class PointsAccount:
    account_id: str
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.account_id:
            raise ValueError("account_id cannot be empty")

    def copy(self) -> "PointsAccount":
        return PointsAccount(
            account_id=self.account_id,
            created_at=self.created_at,
        )


def make_batch(
    account_id: str,
    points: int,
    expired_at: datetime,
    created_at: Optional[datetime] = None,
) -> PointsBatch:
    if points < 0:
        raise InvalidAmountError("points cannot be negative")
    return PointsBatch(
        batch_id=str(uuid4()),
        account_id=account_id,
        total_points=points,
        remaining_points=points,
        frozen_points=0,
        created_at=created_at if created_at is not None else datetime.now(),
        expired_at=expired_at,
    )


def make_frozen_record(
    account_id: str,
    amount: int,
    batch_deductions: Dict[str, int],
) -> FrozenRecord:
    if amount < 0:
        raise InvalidAmountError("amount cannot be negative")
    return FrozenRecord(
        freeze_id=str(uuid4()),
        account_id=account_id,
        total_amount=amount,
        status=FreezeStatus.FROZEN,
        created_at=datetime.now(),
        batch_deductions=dict(batch_deductions),
    )


def make_expired_log(
    account_id: str,
    batch_id: str,
    recycled_points: int,
) -> ExpiredLog:
    return ExpiredLog(
        log_id=str(uuid4()),
        account_id=account_id,
        batch_id=batch_id,
        recycled_points=recycled_points,
        recycled_at=datetime.now(),
    )


def make_account(account_id: str) -> PointsAccount:
    return PointsAccount(account_id=account_id)
