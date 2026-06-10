from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

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
    TenantQuota,
    make_global_quota,
    make_tenant_quota,
)


@dataclass
class QuotaManager:
    _global_quota: Optional[GlobalQuota] = field(default=None)
    _tenant_quotas: Dict[str, TenantQuota] = field(default_factory=dict)
    _tenant_locks: Dict[str, threading.RLock] = field(default_factory=dict)
    _global_lock: threading.RLock = field(default_factory=threading.RLock)

    def _get_or_create_tenant_lock(self, tenant_id: str) -> threading.RLock:
        with self._global_lock:
            if tenant_id not in self._tenant_locks:
                self._tenant_locks[tenant_id] = threading.RLock()
            return self._tenant_locks[tenant_id]

    def _check_tenant_exists(self, tenant_id: str) -> None:
        if tenant_id not in self._tenant_quotas:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

    def _check_global_quota_set(self) -> None:
        if self._global_quota is None:
            raise GlobalQuotaNotSetError("Global quota has not been set")

    def set_global_quota(self, limit: int) -> GlobalQuota:
        if limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        with self._global_lock:
            if self._global_quota is None:
                self._global_quota = make_global_quota(limit)
            else:
                self._global_quota.limit = limit
                if self._global_quota.used > limit:
                    self._global_quota.used = limit
            return self._global_quota.copy()

    def get_global_quota(self) -> GlobalQuota:
        with self._global_lock:
            self._check_global_quota_set()
            return self._global_quota.copy()

    def create_tenant_quota(self, tenant_id: str, limit: int) -> TenantQuota:
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")
        if limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        with self._global_lock:
            if tenant_id in self._tenant_quotas:
                raise TenantExistsError(f"Tenant {tenant_id} already exists")
            quota = make_tenant_quota(tenant_id, limit)
            self._tenant_quotas[tenant_id] = quota
            return quota.copy()

    def update_tenant_quota_limit(self, tenant_id: str, limit: int) -> TenantQuota:
        if limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        with self._global_lock:
            self._check_tenant_exists(tenant_id)
        lock = self._get_or_create_tenant_lock(tenant_id)
        with lock:
            self._tenant_quotas[tenant_id].limit = limit
            if self._tenant_quotas[tenant_id].used > limit:
                self._tenant_quotas[tenant_id].used = limit
            return self._tenant_quotas[tenant_id].copy()

    def get_tenant_quota(self, tenant_id: str) -> TenantQuota:
        with self._global_lock:
            self._check_tenant_exists(tenant_id)
            return self._tenant_quotas[tenant_id].copy()

    def list_tenants(self) -> list[TenantQuota]:
        with self._global_lock:
            return [q.copy() for q in self._tenant_quotas.values()]

    def acquire(self, tenant_id: str, amount: int) -> None:
        if amount < 0:
            raise InvalidQuotaAmountError("amount cannot be negative")
        if amount == 0:
            raise InvalidQuotaAmountError("amount cannot be zero")

        with self._global_lock:
            self._check_global_quota_set()
            self._check_tenant_exists(tenant_id)

        lock = self._get_or_create_tenant_lock(tenant_id)
        with lock:
            with self._global_lock:
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

        lock = self._get_or_create_tenant_lock(tenant_id)
        with lock:
            tenant_used = self._tenant_quotas[tenant_id].used
            if amount > tenant_used:
                raise ReleaseExceedUsedError(
                    f"Release amount exceeds tenant used: release={amount}, "
                    f"tenant_used={tenant_used}"
                )

            with self._global_lock:
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

        lock = self._get_or_create_tenant_lock(tenant_id)
        with lock:
            with self._global_lock:
                released = self._tenant_quotas[tenant_id].used
                self._global_quota.used -= released
                if self._global_quota.used < 0:
                    self._global_quota.used = 0

            self._tenant_quotas[tenant_id].used = 0
            self._tenant_quotas[tenant_id].reset_at = datetime.now()
            return self._tenant_quotas[tenant_id].copy()

    def reset_global_quota(self) -> GlobalQuota:
        with self._global_lock:
            self._check_global_quota_set()

            for tenant_id in self._tenant_quotas:
                lock = self._get_or_create_tenant_lock(tenant_id)
                with lock:
                    self._tenant_quotas[tenant_id].used = 0
                    self._tenant_quotas[tenant_id].reset_at = datetime.now()

            self._global_quota.used = 0
            self._global_quota.reset_at = datetime.now()
            return self._global_quota.copy()

    def reset_all(self) -> None:
        self.reset_global_quota()
