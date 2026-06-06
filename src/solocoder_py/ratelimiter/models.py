from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class RateLimiterError(Exception):
    pass


class InvalidQuotaError(RateLimiterError):
    pass


class QuotaExceededError(RateLimiterError):
    def __init__(self, level: str, key: str) -> None:
        self.level = level
        self.key = key
        super().__init__(f"Quota exceeded at {level} level for key: {key}")


@dataclass
class SubjectQuota:
    subject_id: str
    max_requests: int


@dataclass
class TenantQuota:
    tenant_id: str
    max_requests: int
    subjects: List[SubjectQuota] = field(default_factory=list)


@dataclass
class RateLimitConfig:
    global_max_requests: int
    window_seconds: float
    tenants: List[TenantQuota] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.global_max_requests <= 0:
            raise InvalidQuotaError("global_max_requests must be positive")
        if self.window_seconds <= 0:
            raise InvalidQuotaError("window_seconds must be positive")

        tenant_sum = 0
        seen_tenants: set[str] = set()
        for tenant in self.tenants:
            if tenant.tenant_id in seen_tenants:
                raise InvalidQuotaError(
                    f"Duplicate tenant id {tenant.tenant_id}"
                )
            seen_tenants.add(tenant.tenant_id)
            if tenant.max_requests <= 0:
                raise InvalidQuotaError(
                    f"Tenant {tenant.tenant_id} max_requests must be positive"
                )
            tenant_sum += tenant.max_requests

            subject_sum = 0
            seen_subjects: set[str] = set()
            for subject in tenant.subjects:
                if subject.max_requests <= 0:
                    raise InvalidQuotaError(
                        f"Subject {subject.subject_id} in tenant {tenant.tenant_id} "
                        f"max_requests must be positive"
                    )
                if subject.subject_id in seen_subjects:
                    raise InvalidQuotaError(
                        f"Duplicate subject id {subject.subject_id} in tenant {tenant.tenant_id}"
                    )
                seen_subjects.add(subject.subject_id)
                subject_sum += subject.max_requests

            if subject_sum > tenant.max_requests:
                raise InvalidQuotaError(
                    f"Sum of subject quotas ({subject_sum}) in tenant {tenant.tenant_id} "
                    f"exceeds tenant quota ({tenant.max_requests})"
                )

        if tenant_sum > self.global_max_requests:
            raise InvalidQuotaError(
                f"Sum of tenant quotas ({tenant_sum}) exceeds global quota ({self.global_max_requests})"
            )

    def get_tenant_quota(self, tenant_id: str) -> Optional[int]:
        for tenant in self.tenants:
            if tenant.tenant_id == tenant_id:
                return tenant.max_requests
        return None

    def get_subject_quota(self, tenant_id: str, subject_id: str) -> Optional[int]:
        for tenant in self.tenants:
            if tenant.tenant_id == tenant_id:
                for subject in tenant.subjects:
                    if subject.subject_id == subject_id:
                        return subject.max_requests
                return None
        return None
