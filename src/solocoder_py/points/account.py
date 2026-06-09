from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .exceptions import (
    AccountExistsError,
    AccountNotFoundError,
    FreezeNotFoundError,
    FreezeStateError,
    InsufficientPointsError,
    InvalidAmountError,
    PointsExpiredError,
)
from .models import (
    ExpiredLog,
    FrozenRecord,
    PointsAccount,
    PointsBatch,
    make_account,
    make_batch,
    make_expired_log,
    make_frozen_record,
)


@dataclass
class PointsAccountManager:
    _accounts: Dict[str, PointsAccount] = field(default_factory=dict)
    _batches: Dict[str, List[PointsBatch]] = field(default_factory=dict)
    _frozen_records: Dict[str, FrozenRecord] = field(default_factory=dict)
    _expired_logs: Dict[str, List[ExpiredLog]] = field(default_factory=dict)
    _account_locks: Dict[str, threading.RLock] = field(default_factory=dict)
    _global_lock: threading.RLock = field(default_factory=threading.RLock)

    def _get_or_create_account_lock(self, account_id: str) -> threading.RLock:
        with self._global_lock:
            if account_id not in self._account_locks:
                self._account_locks[account_id] = threading.RLock()
            return self._account_locks[account_id]

    def _check_account_exists(self, account_id: str) -> None:
        if account_id not in self._accounts:
            raise AccountNotFoundError(f"Account {account_id} not found")

    def create_account(self, account_id: str) -> PointsAccount:
        if not account_id:
            raise ValueError("account_id cannot be empty")
        with self._global_lock:
            if account_id in self._accounts:
                raise AccountExistsError(f"Account {account_id} already exists")
            account = make_account(account_id)
            self._accounts[account_id] = account
            self._batches[account_id] = []
            self._expired_logs[account_id] = []
            return account.copy()

    def get_account(self, account_id: str) -> PointsAccount:
        with self._global_lock:
            self._check_account_exists(account_id)
            return self._accounts[account_id].copy()

    def add_points(
        self,
        account_id: str,
        points: int,
        expired_at: datetime,
    ) -> PointsBatch:
        if points < 0:
            raise InvalidAmountError("points cannot be negative")
        if points == 0:
            raise InvalidAmountError("points cannot be zero")

        with self._global_lock:
            self._check_account_exists(account_id)

        lock = self._get_or_create_account_lock(account_id)
        with lock:
            batch = make_batch(account_id, points, expired_at)
            self._batches[account_id].append(batch)
            return batch.copy()

    def get_available_points(
        self, account_id: str, now: Optional[datetime] = None
    ) -> int:
        with self._global_lock:
            self._check_account_exists(account_id)

        check_time = now if now is not None else datetime.now()
        lock = self._get_or_create_account_lock(account_id)
        with lock:
            return self._calc_available_points(account_id, check_time)

    def get_total_points(self, account_id: str) -> int:
        with self._global_lock:
            self._check_account_exists(account_id)

        lock = self._get_or_create_account_lock(account_id)
        with lock:
            return self._calc_total_points(account_id)

    def get_frozen_points(self, account_id: str) -> int:
        with self._global_lock:
            self._check_account_exists(account_id)

        lock = self._get_or_create_account_lock(account_id)
        with lock:
            return self._calc_frozen_points(account_id)

    def _calc_remaining_points(self, account_id: str) -> int:
        total = 0
        for batch in self._batches[account_id]:
            total += batch.remaining_points
        return total

    def _calc_available_points(self, account_id: str, now: Optional[datetime] = None) -> int:
        check_time = now if now is not None else datetime.now()
        total = 0
        for batch in self._batches[account_id]:
            if not batch.is_expired(check_time):
                total += batch.remaining_points
        return total

    def _calc_total_points(self, account_id: str) -> int:
        total = 0
        for batch in self._batches[account_id]:
            total += batch.remaining_points + batch.frozen_points
        return total

    def _calc_frozen_points(self, account_id: str) -> int:
        total = 0
        for batch in self._batches[account_id]:
            total += batch.frozen_points
        return total

    def _get_sorted_unexpired_batches(
        self, account_id: str, now: Optional[datetime] = None
    ) -> List[PointsBatch]:
        check_time = now if now is not None else datetime.now()
        batches = [b for b in self._batches[account_id] if not b.is_expired(check_time)]
        batches.sort(key=lambda b: b.expired_at)
        return batches

    def _deduct_by_fefo(
        self,
        account_id: str,
        amount: int,
        now: Optional[datetime] = None,
    ) -> Dict[str, int]:
        check_time = now if now is not None else datetime.now()
        total_remaining = self._calc_remaining_points(account_id)
        available = self._calc_available_points(account_id, check_time)

        if total_remaining < amount:
            raise InsufficientPointsError(
                f"Insufficient points: total_remaining={total_remaining}, requested={amount}"
            )
        if available < amount:
            raise PointsExpiredError(
                f"Points expired: available={available}, requested={amount}, "
                f"expired_points={total_remaining - available}"
            )

        sorted_batches = self._get_sorted_unexpired_batches(account_id, check_time)
        deductions: Dict[str, int] = {}
        remaining = amount

        for batch in sorted_batches:
            if remaining <= 0:
                break
            deduct = min(batch.remaining_points, remaining)
            if deduct > 0:
                batch.remaining_points -= deduct
                deductions[batch.batch_id] = deduct
                remaining -= deduct

        if remaining > 0:
            raise InsufficientPointsError(
                f"Failed to deduct all points: shortfall={remaining}"
            )

        return deductions

    def _freeze_by_fefo(
        self,
        account_id: str,
        amount: int,
        now: Optional[datetime] = None,
    ) -> Dict[str, int]:
        check_time = now if now is not None else datetime.now()
        total_remaining = self._calc_remaining_points(account_id)
        available = self._calc_available_points(account_id, check_time)

        if total_remaining < amount:
            raise InsufficientPointsError(
                f"Insufficient points: total_remaining={total_remaining}, requested={amount}"
            )
        if available < amount:
            raise PointsExpiredError(
                f"Points expired: available={available}, requested={amount}, "
                f"expired_points={total_remaining - available}"
            )

        sorted_batches = self._get_sorted_unexpired_batches(account_id, check_time)
        deductions: Dict[str, int] = {}
        remaining = amount

        for batch in sorted_batches:
            if remaining <= 0:
                break
            deduct = min(batch.remaining_points, remaining)
            if deduct > 0:
                batch.remaining_points -= deduct
                batch.frozen_points += deduct
                deductions[batch.batch_id] = deduct
                remaining -= deduct

        if remaining > 0:
            raise InsufficientPointsError(
                f"Failed to freeze all points: shortfall={remaining}"
            )

        return deductions

    def consume_points(
        self,
        account_id: str,
        amount: int,
        now: Optional[datetime] = None,
    ) -> Dict[str, int]:
        if amount < 0:
            raise InvalidAmountError("amount cannot be negative")
        if amount == 0:
            raise InvalidAmountError("amount cannot be zero")

        with self._global_lock:
            self._check_account_exists(account_id)

        check_time = now if now is not None else datetime.now()
        lock = self._get_or_create_account_lock(account_id)
        with lock:
            return self._deduct_by_fefo(account_id, amount, check_time)

    def freeze_points(
        self,
        account_id: str,
        amount: int,
        now: Optional[datetime] = None,
    ) -> FrozenRecord:
        if amount < 0:
            raise InvalidAmountError("amount cannot be negative")
        if amount == 0:
            raise InvalidAmountError("amount cannot be zero")

        with self._global_lock:
            self._check_account_exists(account_id)

        check_time = now if now is not None else datetime.now()
        lock = self._get_or_create_account_lock(account_id)
        with lock:
            deductions = self._freeze_by_fefo(account_id, amount, check_time)
            record = make_frozen_record(account_id, amount, deductions)
            self._frozen_records[record.freeze_id] = record
            return record.copy()

    def unfreeze_points(
        self, freeze_id: str, now: Optional[datetime] = None
    ) -> FrozenRecord:
        check_time = now if now is not None else datetime.now()

        with self._global_lock:
            if freeze_id not in self._frozen_records:
                raise FreezeNotFoundError(f"Freeze record {freeze_id} not found")
            record = self._frozen_records[freeze_id]
            account_id = record.account_id
            self._check_account_exists(account_id)

        lock = self._get_or_create_account_lock(account_id)
        with lock:
            if not record.is_frozen:
                raise FreezeStateError(
                    f"Cannot unfreeze: freeze is in state {record.status}"
                )

            for batch_id, amount in record.batch_deductions.items():
                for batch in self._batches[account_id]:
                    if batch.batch_id == batch_id:
                        if batch.frozen_points < amount:
                            raise FreezeStateError(
                                f"Batch {batch_id} has insufficient frozen points"
                            )
                        batch.frozen_points -= amount
                        if batch.is_expired(check_time):
                            log = make_expired_log(account_id, batch_id, amount)
                            self._expired_logs[account_id].append(log)
                        else:
                            batch.remaining_points += amount
                        break

            record.mark_unfrozen()
            return record.copy()

    def consume_frozen_points(self, freeze_id: str) -> FrozenRecord:
        with self._global_lock:
            if freeze_id not in self._frozen_records:
                raise FreezeNotFoundError(f"Freeze record {freeze_id} not found")
            record = self._frozen_records[freeze_id]
            account_id = record.account_id
            self._check_account_exists(account_id)

        lock = self._get_or_create_account_lock(account_id)
        with lock:
            if not record.is_frozen:
                raise FreezeStateError(
                    f"Cannot consume: freeze is in state {record.status}"
                )

            for batch_id, amount in record.batch_deductions.items():
                for batch in self._batches[account_id]:
                    if batch.batch_id == batch_id:
                        if batch.frozen_points < amount:
                            raise FreezeStateError(
                                f"Batch {batch_id} has insufficient frozen points"
                            )
                        batch.frozen_points -= amount
                        break

            record.mark_consumed()
            return record.copy()

    def get_frozen_record(self, freeze_id: str) -> FrozenRecord:
        with self._global_lock:
            if freeze_id not in self._frozen_records:
                raise FreezeNotFoundError(f"Freeze record {freeze_id} not found")
            return self._frozen_records[freeze_id].copy()

    def recycle_expired_points(
        self,
        account_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> List[ExpiredLog]:
        check_time = now if now is not None else datetime.now()
        recycled_logs: List[ExpiredLog] = []

        with self._global_lock:
            if account_id is not None:
                self._check_account_exists(account_id)
                target_accounts = [account_id]
            else:
                target_accounts = list(self._accounts.keys())

        for acc_id in target_accounts:
            lock = self._get_or_create_account_lock(acc_id)
            with lock:
                for batch in self._batches[acc_id]:
                    if batch.is_expired(check_time) and batch.remaining_points > 0:
                        recycled = batch.remaining_points
                        batch.remaining_points = 0
                        log = make_expired_log(acc_id, batch.batch_id, recycled)
                        self._expired_logs[acc_id].append(log)
                        recycled_logs.append(log.copy())

        return recycled_logs

    def get_batches(self, account_id: str) -> List[PointsBatch]:
        with self._global_lock:
            self._check_account_exists(account_id)

        lock = self._get_or_create_account_lock(account_id)
        with lock:
            return [b.copy() for b in self._batches[account_id]]

    def get_expired_logs(self, account_id: str) -> List[ExpiredLog]:
        with self._global_lock:
            self._check_account_exists(account_id)

        lock = self._get_or_create_account_lock(account_id)
        with lock:
            return [l.copy() for l in self._expired_logs[account_id]]

    def list_accounts(self) -> List[PointsAccount]:
        with self._global_lock:
            return [a.copy() for a in self._accounts.values()]
