from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.ratelimiter import (
    InvalidQuotaError,
    ManualClock,
    MultiLevelRateLimiter,
    QuotaExceededError,
    RateLimitConfig,
    SubjectQuota,
    TenantQuota,
)


def make_config(
    global_max: int = 100,
    window: float = 60.0,
    tenants: list[tuple[str, int, list[tuple[str, int]]]] | None = None,
) -> RateLimitConfig:
    tenant_list: list[TenantQuota] = []
    if tenants:
        for tenant_id, tenant_max, subjects in tenants:
            subject_list = [
                SubjectQuota(subject_id=s_id, max_requests=s_max)
                for s_id, s_max in subjects
            ]
            tenant_list.append(
                TenantQuota(
                    tenant_id=tenant_id,
                    max_requests=tenant_max,
                    subjects=subject_list,
                )
            )
    return RateLimitConfig(
        global_max_requests=global_max,
        window_seconds=window,
        tenants=tenant_list,
    )


class TestMultiLevelGlobalLimit:
    def test_global_limit_triggers(self):
        clock = ManualClock()
        config = make_config(
            global_max=3,
            window=60.0,
            tenants=[("t1", 3, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        for _ in range(3):
            limiter.try_acquire("t1", "any_subject")

        with pytest.raises(QuotaExceededError) as exc:
            limiter.try_acquire("t1", "any_subject")
        assert exc.value.level == "global"

    def test_is_allowed_returns_false_on_global_limit(self):
        clock = ManualClock()
        config = make_config(
            global_max=2,
            window=60.0,
            tenants=[("t1", 2, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        assert limiter.is_allowed("t1", "s1") is True
        assert limiter.is_allowed("t1", "s1") is True
        assert limiter.is_allowed("t1", "s1") is True

        assert limiter.get_global_count() == 0
        assert limiter.get_tenant_count("t1") == 0

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")
        assert limiter.is_allowed("t1", "s1") is False
        assert limiter.get_global_count() == 2

    def test_is_allowed_is_non_consuming(self):
        clock = ManualClock()
        config = make_config(
            global_max=5,
            window=60.0,
            tenants=[("t1", 5, [("s1", 3), ("s2", 2)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        for _ in range(10):
            assert limiter.is_allowed("t1", "s1") is True

        assert limiter.get_global_count() == 0
        assert limiter.get_tenant_count("t1") == 0
        assert limiter.get_subject_count("t1", "s1") == 0

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")

        assert limiter.is_allowed("t1", "s1") is False
        assert limiter.is_allowed("t1", "s2") is True
        assert limiter.get_subject_count("t1", "s1") == 3


class TestMultiLevelTenantLimit:
    def test_tenant_limit_triggers_independently(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 2, []), ("t2", 98, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s2")

        with pytest.raises(QuotaExceededError) as exc:
            limiter.try_acquire("t1", "s3")
        assert exc.value.level == "tenant"

        limiter.try_acquire("t2", "s1")
        limiter.try_acquire("t2", "s2")

    def test_tenants_are_independent(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 1, []), ("t2", 1, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t2", "s1")

        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t1", "s2")
        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t2", "s2")


class TestMultiLevelSubjectLimit:
    def test_subject_limit_triggers(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 100, [("s1", 2), ("s2", 98)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")

        with pytest.raises(QuotaExceededError) as exc:
            limiter.try_acquire("t1", "s1")
        assert exc.value.level == "subject"

        limiter.try_acquire("t1", "s2")
        limiter.try_acquire("t1", "s2")

    def test_subject_without_config_passes(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 10, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        for i in range(10):
            limiter.try_acquire("t1", f"unknown_subject_{i}")

        with pytest.raises(QuotaExceededError) as exc:
            limiter.try_acquire("t1", "unknown_subject_extra")
        assert exc.value.level == "tenant"

    def test_subjects_are_independent_within_tenant(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 100, [("s1", 1), ("s2", 1)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s2")

        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t1", "s1")
        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t1", "s2")


class TestMultiLevelRollback:
    def test_tenant_limit_rolls_back_global(self):
        clock = ManualClock()
        config = make_config(
            global_max=10,
            window=60.0,
            tenants=[("t1", 2, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")

        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t1", "s1")

        assert limiter.get_global_count() == 2

    def test_subject_limit_rolls_back_tenant_and_global(self):
        clock = ManualClock()
        config = make_config(
            global_max=10,
            window=60.0,
            tenants=[("t1", 10, [("s1", 2)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")

        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t1", "s1")

        assert limiter.get_global_count() == 2
        assert limiter.get_tenant_count("t1") == 2
        assert limiter.get_subject_count("t1", "s1") == 2


class TestMultiLevelUnknownTenant:
    def test_unknown_tenant_raises(self):
        clock = ManualClock()
        config = make_config(global_max=10, window=60.0, tenants=[("t1", 5, [])])
        limiter = MultiLevelRateLimiter(config, clock=clock)

        with pytest.raises(InvalidQuotaError, match="No quota configured for tenant"):
            limiter.try_acquire("unknown_tenant", "s1")


class TestMultiLevelWindowSliding:
    def test_global_quota_recovers_after_window(self):
        clock = ManualClock(start_time=0.0)
        config = make_config(
            global_max=2,
            window=10.0,
            tenants=[("t1", 2, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")
        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t1", "s1")

        clock.advance(10.0)
        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")

    def test_tenant_quota_recovers_after_window(self):
        clock = ManualClock(start_time=0.0)
        config = make_config(
            global_max=100,
            window=10.0,
            tenants=[("t1", 2, []), ("t2", 98, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")
        with pytest.raises(QuotaExceededError):
            limiter.try_acquire("t1", "s1")

        clock.advance(10.0)
        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")


class TestMultiLevelCounts:
    def test_counts_reflect_limits(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 10, [("s1", 5), ("s2", 3)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s1")
        limiter.try_acquire("t1", "s2")

        assert limiter.get_global_count() == 3
        assert limiter.get_tenant_count("t1") == 3
        assert limiter.get_subject_count("t1", "s1") == 2
        assert limiter.get_subject_count("t1", "s2") == 1
        assert limiter.get_tenant_count("nonexistent") == 0
        assert limiter.get_subject_count("t1", "nonexistent") == 0


class TestMultiLevelConcurrency:
    def test_concurrent_try_acquire_does_not_exceed_global_quota(self):
        clock = ManualClock()
        config = make_config(
            global_max=10,
            window=60.0,
            tenants=[("t1", 10, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        success_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal success_count
            for _ in range(20):
                try:
                    limiter.try_acquire("t1", "s1")
                    with lock:
                        success_count += 1
                except QuotaExceededError:
                    pass

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert success_count == 10
        assert limiter.get_global_count() == 10
        assert limiter.get_tenant_count("t1") == 10

    def test_concurrent_try_acquire_does_not_exceed_tenant_quota(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 7, []), ("t2", 93, [])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        success_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal success_count
            for _ in range(20):
                try:
                    limiter.try_acquire("t1", "any")
                    with lock:
                        success_count += 1
                except QuotaExceededError:
                    pass

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert success_count == 7
        assert limiter.get_tenant_count("t1") == 7
        assert limiter.get_tenant_count("t2") == 0

    def test_concurrent_try_acquire_does_not_exceed_subject_quota(self):
        clock = ManualClock()
        config = make_config(
            global_max=100,
            window=60.0,
            tenants=[("t1", 100, [("s1", 5), ("s2", 95)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        success_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal success_count
            for _ in range(20):
                try:
                    limiter.try_acquire("t1", "s1")
                    with lock:
                        success_count += 1
                except QuotaExceededError:
                    pass

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert success_count == 5
        assert limiter.get_subject_count("t1", "s1") == 5
        assert limiter.get_subject_count("t1", "s2") == 0
        assert limiter.get_tenant_count("t1") == 5
        assert limiter.get_global_count() == 5

    def test_concurrent_rollback_does_not_corrupt_counts(self):
        clock = ManualClock()
        config = make_config(
            global_max=3,
            window=60.0,
            tenants=[("t1", 3, [("s1", 2), ("s2", 1)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        barrier = threading.Barrier(4)
        errors: list[Exception] = []
        s1_success = 0
        s2_success = 0
        count_lock = threading.Lock()

        def worker_s1():
            nonlocal s1_success
            try:
                barrier.wait(timeout=5)
                for _ in range(10):
                    try:
                        limiter.try_acquire("t1", "s1")
                        with count_lock:
                            s1_success += 1
                    except QuotaExceededError:
                        pass
            except Exception as e:
                errors.append(e)

        def worker_s2():
            nonlocal s2_success
            try:
                barrier.wait(timeout=5)
                for _ in range(10):
                    try:
                        limiter.try_acquire("t1", "s2")
                        with count_lock:
                            s2_success += 1
                    except QuotaExceededError:
                        pass
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker_s1),
            threading.Thread(target=worker_s1),
            threading.Thread(target=worker_s2),
            threading.Thread(target=worker_s2),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert s1_success == 2
        assert s2_success == 1
        assert limiter.get_subject_count("t1", "s1") == 2
        assert limiter.get_subject_count("t1", "s2") == 1
        assert limiter.get_tenant_count("t1") == 3
        assert limiter.get_global_count() == 3

    def test_concurrent_is_allowed_does_not_modify_counts(self):
        clock = ManualClock()
        config = make_config(
            global_max=5,
            window=60.0,
            tenants=[("t1", 5, [("s1", 3)])],
        )
        limiter = MultiLevelRateLimiter(config, clock=clock)

        barrier = threading.Barrier(4)

        def worker():
            barrier.wait(timeout=5)
            for _ in range(50):
                limiter.is_allowed("t1", "s1")

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert limiter.get_global_count() == 0
        assert limiter.get_tenant_count("t1") == 0
        assert limiter.get_subject_count("t1", "s1") == 0
