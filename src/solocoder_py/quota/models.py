from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .exceptions import InvalidQuotaAmountError


@dataclass
class GlobalQuota:
    quota_id: str
    limit: int
    used: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    reset_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.quota_id:
            raise ValueError("quota_id cannot be empty")
        if self.limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        if self.used < 0:
            raise InvalidQuotaAmountError("used cannot be negative")
        if self.used > self.limit:
            raise InvalidQuotaAmountError("used cannot exceed limit")

    @property
    def remaining(self) -> int:
        return self.limit - self.used

    def copy(self) -> "GlobalQuota":
        return GlobalQuota(
            quota_id=self.quota_id,
            limit=self.limit,
            used=self.used,
            created_at=self.created_at,
            reset_at=self.reset_at,
        )


@dataclass
class TenantQuota:
    tenant_id: str
    limit: int
    used: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    reset_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.tenant_id:
            raise ValueError("tenant_id cannot be empty")
        if self.limit < 0:
            raise InvalidQuotaAmountError("limit cannot be negative")
        if self.used < 0:
            raise InvalidQuotaAmountError("used cannot be negative")
        if self.used > self.limit:
            raise InvalidQuotaAmountError("used cannot exceed limit")

    @property
    def remaining(self) -> int:
        return self.limit - self.used

    def copy(self) -> "TenantQuota":
        return TenantQuota(
            tenant_id=self.tenant_id,
            limit=self.limit,
            used=self.used,
            created_at=self.created_at,
            reset_at=self.reset_at,
        )


def make_global_quota(limit: int) -> GlobalQuota:
    if limit < 0:
        raise InvalidQuotaAmountError("limit cannot be negative")
    return GlobalQuota(
        quota_id=str(uuid4()),
        limit=limit,
        used=0,
    )


def make_tenant_quota(tenant_id: str, limit: int) -> TenantQuota:
    if not tenant_id:
        raise ValueError("tenant_id cannot be empty")
    if limit < 0:
        raise InvalidQuotaAmountError("limit cannot be negative")
    return TenantQuota(
        tenant_id=tenant_id,
        limit=limit,
        used=0,
    )
