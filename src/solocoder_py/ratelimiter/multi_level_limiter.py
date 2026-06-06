from __future__ import annotations

import threading
from typing import Dict, Optional

from .clock import Clock, SystemClock
from .models import (
    InvalidQuotaError,
    QuotaExceededError,
    RateLimitConfig,
)
from .sliding_window import SlidingWindowRateLimiter


class MultiLevelRateLimiter:
    def __init__(
        self,
        config: RateLimitConfig,
        clock: Clock | None = None,
    ) -> None:
        self._config: RateLimitConfig = config
        self._clock: Clock = clock or SystemClock()
        self._lock: threading.RLock = threading.RLock()

        self._global_limiter: SlidingWindowRateLimiter = SlidingWindowRateLimiter(
            max_requests=config.global_max_requests,
            window_seconds=config.window_seconds,
            clock=self._clock,
        )

        self._tenant_limiters: Dict[str, SlidingWindowRateLimiter] = {}
        for tenant in config.tenants:
            self._tenant_limiters[tenant.tenant_id] = SlidingWindowRateLimiter(
                max_requests=tenant.max_requests,
                window_seconds=config.window_seconds,
                clock=self._clock,
            )

        self._subject_limiters: Dict[tuple[str, str], SlidingWindowRateLimiter] = {}
        for tenant in config.tenants:
            for subject in tenant.subjects:
                key = (tenant.tenant_id, subject.subject_id)
                self._subject_limiters[key] = SlidingWindowRateLimiter(
                    max_requests=subject.max_requests,
                    window_seconds=config.window_seconds,
                    clock=self._clock,
                )

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    def _ensure_tenant_limiter(
        self, tenant_id: str
    ) -> SlidingWindowRateLimiter:
        with self._lock:
            limiter = self._tenant_limiters.get(tenant_id)
            if limiter is None:
                tenant_quota = self._config.get_tenant_quota(tenant_id)
                if tenant_quota is None:
                    raise InvalidQuotaError(
                        f"No quota configured for tenant: {tenant_id}"
                    )
                limiter = SlidingWindowRateLimiter(
                    max_requests=tenant_quota,
                    window_seconds=self._config.window_seconds,
                    clock=self._clock,
                )
                self._tenant_limiters[tenant_id] = limiter
            return limiter

    def _ensure_subject_limiter(
        self, tenant_id: str, subject_id: str
    ) -> Optional[SlidingWindowRateLimiter]:
        with self._lock:
            key = (tenant_id, subject_id)
            limiter = self._subject_limiters.get(key)
            if limiter is None:
                subject_quota = self._config.get_subject_quota(tenant_id, subject_id)
                if subject_quota is None:
                    return None
                limiter = SlidingWindowRateLimiter(
                    max_requests=subject_quota,
                    window_seconds=self._config.window_seconds,
                    clock=self._clock,
                )
                self._subject_limiters[key] = limiter
            return limiter

    def try_acquire(self, tenant_id: str, subject_id: str) -> None:
        with self._lock:
            global_acquired = False
            tenant_acquired = False
            tenant_limiter: SlidingWindowRateLimiter | None = None
            subject_limiter: SlidingWindowRateLimiter | None = None

            try:
                if not self._global_limiter.try_acquire():
                    raise QuotaExceededError("global", "global")
                global_acquired = True

                tenant_limiter = self._ensure_tenant_limiter(tenant_id)
                if not tenant_limiter.try_acquire():
                    raise QuotaExceededError("tenant", tenant_id)
                tenant_acquired = True

                subject_limiter = self._ensure_subject_limiter(tenant_id, subject_id)
                if subject_limiter is not None:
                    if not subject_limiter.try_acquire():
                        raise QuotaExceededError("subject", subject_id)
            except Exception:
                if tenant_acquired and tenant_limiter is not None:
                    tenant_limiter._rollback_last()
                if global_acquired:
                    self._global_limiter._rollback_last()
                raise

    def is_allowed(self, tenant_id: str, subject_id: str) -> bool:
        with self._lock:
            if not self._global_limiter.can_acquire():
                return False

            try:
                tenant_limiter = self._ensure_tenant_limiter(tenant_id)
            except InvalidQuotaError:
                return False
            if not tenant_limiter.can_acquire():
                return False

            subject_limiter = self._ensure_subject_limiter(tenant_id, subject_id)
            if subject_limiter is not None:
                if not subject_limiter.can_acquire():
                    return False

            return True

    def get_global_count(self) -> int:
        return self._global_limiter.current_count()

    def get_tenant_count(self, tenant_id: str) -> int:
        limiter = self._tenant_limiters.get(tenant_id)
        if limiter is None:
            return 0
        return limiter.current_count()

    def get_subject_count(self, tenant_id: str, subject_id: str) -> int:
        key = (tenant_id, subject_id)
        limiter = self._subject_limiters.get(key)
        if limiter is None:
            return 0
        return limiter.current_count()
