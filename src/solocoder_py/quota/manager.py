from __future__ import annotations

import calendar
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from .clock import Clock, SystemClock
from .exceptions import (
    GlobalQuotaNotSetError,
    InvalidQuotaAmountError,
    QuotaLimitExceededError,
    ReleaseExceedUsedError,
    TenantExistsError,
    TenantNotFoundError,
)
from .models import (
    GlobalQuota,
    QuotaPeriod,
    TenantQuota,
    make_global_quota,
    make_tenant_quota,
)


def _period_delta(period: QuotaPeriod) -> Optional[timedelta]:
    if period == QuotaPeriod.HOURLY:
        return timedelta(hours=1)
    if period == QuotaPeriod.DAILY:
        return timedelta(days=1)
    if period == QuotaPeriod.WEEKLY:
        return timedelta(weeks=1)
    return None


def _add_months(dt: datetime, months: int) -> datetime:
    total_month = dt.month - 1 + months
    new_year = dt.year + total_month // 12
    new_month = total_month % 12 + 1
    _, max_day = calendar.monthrange(new_year, new_month)
    new_day = min(dt.day, max_day)
    return dt.replace(year=new_year, month=new_month, day=new_day)


def _is_period_expired_since(
    period_start: datetime, now: datetime, period: QuotaPeriod
) -> bool:
    if period == QuotaPeriod.NONE:
        return False
    delta = _period_delta(period)
    if delta is not None:
        elapsed = now - period_start
        return elapsed >= delta
    if period == QuotaPeriod.MONTHLY:
        boundary = _add_months(period_start, 1)
        return now >= boundary
    return False


@dataclass
class QuotaManager:
    _clock: Clock = field(default_factory=SystemClock)
    _global_quota: Optional[GlobalQuota] = field(default=None)
    _tenant_quotas: Dict[str, TenantQuota] = field(default_factory=dict)
    _tenant_locks: Dict[str, threading.RLock] = field(default_factory=dict)
    _global_lock: threading.RLock = field(default_factory=threading.RLock)

    def _get_or_create_tenant_lock(self, tenant_id: str) -> threading.RLock:
        if tenant_id not in self._tenant_locks:
            self._tenant_locks[tenant_id] = threading.RLock()
        return self._tenant_locks[tenant_id]

    def _check_tenant_exists(self, tenant_id: str) -> None:
        if tenant_id not in self._tenant_quotas:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

    def _check_global_quota_set(self) -> None:
        if self._global_quota is None:
            raise GlobalQuotaNotSetError("Global quota has not been set")

    def _is_period_expired(
        self, period_start: Optional[datetime], period: QuotaPeriod, now: datetime
    ) -> bool:
        if period == QuotaPeriod.NONE or period_start is None:
            return False
        return _is_period_expired_since(period_start, now, period)

    def _maybe_reset_global_period(self) -> None:
        if self._global_quota is None:
            return
        now = self._clock.now()
        if self._is_period_expired(
            self._global_quota.period_start, self._global_quota.period, now
        ):
            for tenant_id in self._tenant_quotas:
                tenant_lock = self._get_or_create_tenant_lock(tenant_id)
                with tenant_lock:
                    self._tenant_quotas[tenant_id].used = 0
                    self._tenant_quotas[tenant_id].period_start = now
                    self._tenant_quotas[tenant_id].reset_at = now
            self._global_quota.used = 0
            self._global_quota.period_start = now
            self._global_quota.reset_at = now

    def _maybe_reset_tenant_period(self, tenant_id: str) -> None:
        if self._global_quota is None:
            return
        now = self._clock.now()
        global_expired = self._is_period_expired(
            self._global_quota.period_start, self._global_quota.period, now
        )
        if global_expired:
            self._maybe_reset_global_period()
            return
        tenant_expired = self._is_period_expired(
            self._tenant_quotas[tenant_id].period_start,
            self._tenant_quotas[tenant_id].period,
            now,
        )
        if tenant_expired:
            released = self._tenant_quotas[tenant_id].used
            self._global_quota.used -= released
            if self._global_quota.used < 0:
                self._global_quota.used = 0
            self._tenant_quotas[tenant_id].used = 0
            self._tenant_quotas[tenant_id].period_start = now
            self._tenant_quotas[tenant_id].reset_at = now

    def set_global_quota(
        self, limit: int, period: QuotaPeriod = QuotaPeriod.NONE
    ) -> GlobalQuota:
        if limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        with self._global_lock:
            now = self._clock.now()
            if self._global_quota is None:
                self._global_quota = make_global_quota(limit, period)
                if period != QuotaPeriod.NONE:
                    self._global_quota.period_start = now
            else:
                self._global_quota.limit = limit
                self._global_quota.period = period
                if period != QuotaPeriod.NONE and self._global_quota.period_start is None:
                    self._global_quota.period_start = now
            return self._global_quota.copy()

    def get_global_quota(self) -> GlobalQuota:
        with self._global_lock:
            self._check_global_quota_set()
            self._maybe_reset_global_period()
            return self._global_quota.copy()

    def create_tenant_quota(
        self, tenant_id: str, limit: int, period: QuotaPeriod = QuotaPeriod.NONE
    ) -> TenantQuota:
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")
        if limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        with self._global_lock:
            if tenant_id in self._tenant_quotas:
                raise TenantExistsError(f"Tenant {tenant_id} already exists")
            now = self._clock.now()
            quota = make_tenant_quota(tenant_id, limit, period)
            if period != QuotaPeriod.NONE:
                quota.period_start = now
            self._tenant_quotas[tenant_id] = quota
            return quota.copy()

    def update_tenant_quota_limit(
        self, tenant_id: str, limit: int, period: Optional[QuotaPeriod] = None
    ) -> TenantQuota:
        if limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        with self._global_lock:
            self._check_global_quota_set()
            self._check_tenant_exists(tenant_id)
            tenant_lock = self._get_or_create_tenant_lock(tenant_id)
            with tenant_lock:
                self._maybe_reset_tenant_period(tenant_id)
                self._tenant_quotas[tenant_id].limit = limit
                if period is not None:
                    self._tenant_quotas[tenant_id].period = period
                    if period != QuotaPeriod.NONE and self._tenant_quotas[tenant_id].period_start is None:
                        self._tenant_quotas[tenant_id].period_start = self._clock.now()
                return self._tenant_quotas[tenant_id].copy()

    def get_tenant_quota(self, tenant_id: str) -> TenantQuota:
        with self._global_lock:
            self._check_global_quota_set()
            self._check_tenant_exists(tenant_id)
            tenant_lock = self._get_or_create_tenant_lock(tenant_id)
            with tenant_lock:
                self._maybe_reset_tenant_period(tenant_id)
                return self._tenant_quotas[tenant_id].copy()

    def list_tenants(self) -> list[TenantQuota]:
        with self._global_lock:
            self._maybe_reset_global_period()
            return [q.copy() for q in self._tenant_quotas.values()]

    def acquire(self, tenant_id: str, amount: int) -> None:
        if amount < 0:
            raise InvalidQuotaAmountError("amount cannot be negative")
        if amount == 0:
            raise InvalidQuotaAmountError("amount cannot be zero")

        with self._global_lock:
            self._check_global_quota_set()
            self._check_tenant_exists(tenant_id)
            tenant_lock = self._get_or_create_tenant_lock(tenant_id)
            with tenant_lock:
                self._maybe_reset_tenant_period(tenant_id)
                global_remaining = self._global_quota.remaining
                tenant_remaining = self._tenant_quotas[tenant_id].remaining

                if tenant_remaining < amount and global_remaining < amount:
                    raise QuotaLimitExceededError(
                        f"Quota exceeded: tenant remaining={tenant_remaining}, "
                        f"global remaining={global_remaining}, requested={amount}",
                        reason="both_tenant_and_global_insufficient",
                    )
                if tenant_remaining < amount:
                    raise QuotaLimitExceededError(
                        f"Tenant quota exceeded: tenant remaining={tenant_remaining}, "
                        f"requested={amount}",
                        reason="tenant_insufficient",
                    )
                if global_remaining < amount:
                    raise QuotaLimitExceededError(
                        f"Global quota exceeded: global remaining={global_remaining}, "
                        f"requested={amount}",
                        reason="global_insufficient",
                    )

                self._tenant_quotas[tenant_id].used += amount
                self._global_quota.used += amount

    def release(self, tenant_id: str, amount: int) -> None:
        if amount < 0:
            raise InvalidQuotaAmountError("amount cannot be negative")
        if amount == 0:
            raise InvalidQuotaAmountError("amount cannot be zero")

        with self._global_lock:
            self._check_global_quota_set()
            self._check_tenant_exists(tenant_id)
            tenant_lock = self._get_or_create_tenant_lock(tenant_id)
            with tenant_lock:
                self._maybe_reset_tenant_period(tenant_id)
                tenant_used = self._tenant_quotas[tenant_id].used
                if amount > tenant_used:
                    raise ReleaseExceedUsedError(
                        f"Release amount exceeds tenant used: release={amount}, "
                        f"tenant_used={tenant_used}"
                    )
                global_used = self._global_quota.used
                if amount > global_used:
                    raise ReleaseExceedUsedError(
                        f"Release amount exceeds global used: release={amount}, "
                        f"global_used={global_used}"
                    )
                self._tenant_quotas[tenant_id].used -= amount
                self._global_quota.used -= amount

    def reset_tenant_quota(self, tenant_id: str) -> TenantQuota:
        with self._global_lock:
            self._check_global_quota_set()
            self._check_tenant_exists(tenant_id)
            tenant_lock = self._get_or_create_tenant_lock(tenant_id)
            with tenant_lock:
                released = self._tenant_quotas[tenant_id].used
                self._global_quota.used -= released
                if self._global_quota.used < 0:
                    self._global_quota.used = 0
                now = self._clock.now()
                self._tenant_quotas[tenant_id].used = 0
                self._tenant_quotas[tenant_id].reset_at = now
                if self._tenant_quotas[tenant_id].period != QuotaPeriod.NONE:
                    self._tenant_quotas[tenant_id].period_start = now
                return self._tenant_quotas[tenant_id].copy()

    def reset_global_quota(self) -> GlobalQuota:
        with self._global_lock:
            self._check_global_quota_set()
            now = self._clock.now()
            for tenant_id in self._tenant_quotas:
                tenant_lock = self._get_or_create_tenant_lock(tenant_id)
                with tenant_lock:
                    self._tenant_quotas[tenant_id].used = 0
                    self._tenant_quotas[tenant_id].reset_at = now
                    if self._tenant_quotas[tenant_id].period != QuotaPeriod.NONE:
                        self._tenant_quotas[tenant_id].period_start = now
            self._global_quota.used = 0
            self._global_quota.reset_at = now
            if self._global_quota.period != QuotaPeriod.NONE:
                self._global_quota.period_start = now
            return self._global_quota.copy()

    def reset_all(self) -> None:
        self.reset_global_quota()
