from __future__ import annotations

import pytest

from solocoder_py.ratelimiter import (
    InvalidQuotaError,
    RateLimitConfig,
    SubjectQuota,
    TenantQuota,
)


class TestRateLimitConfigValidation:
    def test_valid_minimal_config(self):
        config = RateLimitConfig(global_max_requests=100, window_seconds=60.0)
        assert config.global_max_requests == 100
        assert config.window_seconds == 60.0

    def test_global_max_requests_must_be_positive(self):
        with pytest.raises(InvalidQuotaError, match="global_max_requests must be positive"):
            RateLimitConfig(global_max_requests=0, window_seconds=60.0)
        with pytest.raises(InvalidQuotaError, match="global_max_requests must be positive"):
            RateLimitConfig(global_max_requests=-1, window_seconds=60.0)

    def test_window_seconds_must_be_positive(self):
        with pytest.raises(InvalidQuotaError, match="window_seconds must be positive"):
            RateLimitConfig(global_max_requests=100, window_seconds=0.0)
        with pytest.raises(InvalidQuotaError, match="window_seconds must be positive"):
            RateLimitConfig(global_max_requests=100, window_seconds=-1.0)

    def test_tenant_max_requests_must_be_positive(self):
        with pytest.raises(InvalidQuotaError, match="Tenant.*max_requests must be positive"):
            RateLimitConfig(
                global_max_requests=100,
                window_seconds=60.0,
                tenants=[TenantQuota(tenant_id="t1", max_requests=0)],
            )

    def test_subject_max_requests_must_be_positive(self):
        with pytest.raises(InvalidQuotaError, match="Subject.*max_requests must be positive"):
            RateLimitConfig(
                global_max_requests=100,
                window_seconds=60.0,
                tenants=[
                    TenantQuota(
                        tenant_id="t1",
                        max_requests=50,
                        subjects=[SubjectQuota(subject_id="s1", max_requests=0)],
                    )
                ],
            )

    def test_sum_of_tenant_quotas_exceeds_global_raises(self):
        with pytest.raises(
            InvalidQuotaError,
            match="Sum of tenant quotas \\(150\\) exceeds global quota \\(100\\)",
        ):
            RateLimitConfig(
                global_max_requests=100,
                window_seconds=60.0,
                tenants=[
                    TenantQuota(tenant_id="t1", max_requests=50),
                    TenantQuota(tenant_id="t2", max_requests=50),
                    TenantQuota(tenant_id="t3", max_requests=50),
                ],
            )

    def test_sum_of_tenant_quotas_equals_global_is_valid(self):
        config = RateLimitConfig(
            global_max_requests=100,
            window_seconds=60.0,
            tenants=[
                TenantQuota(tenant_id="t1", max_requests=60),
                TenantQuota(tenant_id="t2", max_requests=40),
            ],
        )
        assert len(config.tenants) == 2

    def test_sum_of_subject_quotas_exceeds_tenant_raises(self):
        with pytest.raises(
            InvalidQuotaError,
            match="Sum of subject quotas \\(60\\) in tenant t1 exceeds tenant quota \\(50\\)",
        ):
            RateLimitConfig(
                global_max_requests=100,
                window_seconds=60.0,
                tenants=[
                    TenantQuota(
                        tenant_id="t1",
                        max_requests=50,
                        subjects=[
                            SubjectQuota(subject_id="s1", max_requests=30),
                            SubjectQuota(subject_id="s2", max_requests=30),
                        ],
                    )
                ],
            )

    def test_sum_of_subject_quotas_equals_tenant_is_valid(self):
        config = RateLimitConfig(
            global_max_requests=100,
            window_seconds=60.0,
            tenants=[
                TenantQuota(
                    tenant_id="t1",
                    max_requests=50,
                    subjects=[
                        SubjectQuota(subject_id="s1", max_requests=30),
                        SubjectQuota(subject_id="s2", max_requests=20),
                    ],
                )
            ],
        )
        assert config.get_subject_quota("t1", "s1") == 30
        assert config.get_subject_quota("t1", "s2") == 20

    def test_duplicate_subject_id_raises(self):
        with pytest.raises(InvalidQuotaError, match="Duplicate subject id s1"):
            RateLimitConfig(
                global_max_requests=100,
                window_seconds=60.0,
                tenants=[
                    TenantQuota(
                        tenant_id="t1",
                        max_requests=50,
                        subjects=[
                            SubjectQuota(subject_id="s1", max_requests=10),
                            SubjectQuota(subject_id="s1", max_requests=20),
                        ],
                    )
                ],
            )

    def test_duplicate_tenant_id_raises(self):
        with pytest.raises(InvalidQuotaError, match="Duplicate tenant id t1"):
            RateLimitConfig(
                global_max_requests=100,
                window_seconds=60.0,
                tenants=[
                    TenantQuota(tenant_id="t1", max_requests=30),
                    TenantQuota(tenant_id="t1", max_requests=40),
                ],
            )


class TestRateLimitConfigLookups:
    def test_get_tenant_quota_existing(self):
        config = RateLimitConfig(
            global_max_requests=100,
            window_seconds=60.0,
            tenants=[TenantQuota(tenant_id="t1", max_requests=50)],
        )
        assert config.get_tenant_quota("t1") == 50

    def test_get_tenant_quota_nonexistent(self):
        config = RateLimitConfig(global_max_requests=100, window_seconds=60.0)
        assert config.get_tenant_quota("nonexistent") is None

    def test_get_subject_quota_existing(self):
        config = RateLimitConfig(
            global_max_requests=100,
            window_seconds=60.0,
            tenants=[
                TenantQuota(
                    tenant_id="t1",
                    max_requests=50,
                    subjects=[SubjectQuota(subject_id="s1", max_requests=20)],
                )
            ],
        )
        assert config.get_subject_quota("t1", "s1") == 20

    def test_get_subject_quota_wrong_tenant(self):
        config = RateLimitConfig(
            global_max_requests=100,
            window_seconds=60.0,
            tenants=[
                TenantQuota(
                    tenant_id="t1",
                    max_requests=50,
                    subjects=[SubjectQuota(subject_id="s1", max_requests=20)],
                )
            ],
        )
        assert config.get_subject_quota("t2", "s1") is None

    def test_get_subject_quota_nonexistent_subject(self):
        config = RateLimitConfig(
            global_max_requests=100,
            window_seconds=60.0,
            tenants=[TenantQuota(tenant_id="t1", max_requests=50)],
        )
        assert config.get_subject_quota("t1", "nonexistent") is None
