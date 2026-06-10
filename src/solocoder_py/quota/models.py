from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from .exceptions import InvalidQuotaAmountError


class QuotaPeriod(str, Enum):
    NONE = "none"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class GlobalQuota:
    quota_id: str
    limit: int
    period: QuotaPeriod = QuotaPeriod.NONE
    used: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    period_start: Optional[datetime] = None
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
            period=self.period,
            used=self.used,
            created_at=self.created_at,
            period_start=self.period_start,
            reset_at=self.reset_at,
        )


@dataclass
class TenantQuota:
    tenant_id: str
    limit: int
    period: QuotaPeriod = QuotaPeriod.NONE
    used: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    period_start: Optional[datetime] = None
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
            period=self.period,
            used=self.used,
            created_at=self.created_at,
            period_start=self.period_start,
            reset_at=self.reset_at,
        )


def make_global_quota(limit: int, period: QuotaPeriod = QuotaPeriod.NONE) -> GlobalQuota:
    if limit < 0:
        raise InvalidQuotaAmountError("limit cannot be negative")
    now = datetime.now()
    return GlobalQuota(
        quota_id=str(uuid4()),
        limit=limit,
        period=period,
        used=0,
        created_at=now,
        period_start=None,
    )


def make_tenant_quota(
    tenant_id: str, limit: int, period: QuotaPeriod = QuotaPeriod.NONE
) -> TenantQuota:
    if not tenant_id:
        raise ValueError("tenant_id cannot be empty")
    if limit < 0:
        raise InvalidQuotaAmountError("limit cannot be negative")
    now = datetime.now()
    return TenantQuota(
        tenant_id=tenant_id,
        limit=limit,
        period=period,
        used=0,
        created_at=now,
        period_start=None,
    )
