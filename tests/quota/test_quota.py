from __future__ import annotations

import threading
from datetime import datetime

import pytest

from solocoder_py.quota import (
    GlobalQuota,
    GlobalQuotaNotSetError,
    InvalidQuotaAmountError,
    QuotaError,
    QuotaLimitExceededError,
    QuotaManager,
    ReleaseExceedUsedError,
    TenantError,
    TenantExistsError,
    TenantNotFoundError,
    TenantQuota,
    make_global_quota,
    make_tenant_quota,
)
from .conftest import make_manager


class TestModels:
    def test_global_quota_creation(self):
        gq = make_global_quota(100)
        assert gq.limit == 100
        assert gq.used == 0
        assert gq.remaining == 100
        assert gq.quota_id

    def test_global_quota_negative_limit_raises(self):
        with pytest.raises(InvalidQuotaAmountError):
            make_global_quota(-1)

    def test_tenant_quota_creation(self):
        tq = make_tenant_quota("tenant-1", 50)
        assert tq.tenant_id == "tenant-1"
        assert tq.limit == 50
        assert tq.used == 0
        assert tq.remaining == 50

    def test_tenant_quota_empty_id_raises(self):
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            make_tenant_quota("", 50)

    def test_tenant_quota_negative_limit_raises(self):
        with pytest.raises(InvalidQuotaAmountError):
            make_tenant_quota("t", -1)

    def test_quota_used_exceeds_limit_raises(self):
        with pytest.raises(InvalidQuotaAmountError):
            GlobalQuota(quota_id="q", limit=10, used=20)
        with pytest.raises(InvalidQuotaAmountError):
            TenantQuota(tenant_id="t", limit=10, used=20)

    def test_quota_copy_is_independent(self):
        tq = make_tenant_quota("t1", 100)
        copy = tq.copy()
        copy.limit = 999
        copy.used = 500
        assert tq.limit == 100
        assert tq.used == 0


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_quota_error(self):
        assert issubclass(TenantError, QuotaError)
        assert issubclass(TenantNotFoundError, QuotaError)
        assert issubclass(TenantExistsError, QuotaError)
        assert issubclass(QuotaLimitExceededError, QuotaError)
        assert issubclass(InvalidQuotaAmountError, QuotaError)
        assert issubclass(ReleaseExceedUsedError, QuotaError)
        assert issubclass(GlobalQuotaNotSetError, QuotaError)

    def test_quota_limit_exceeded_has_reason(self):
        err = QuotaLimitExceededError("msg", "tenant_insufficient")
        assert err.reason == "tenant_insufficient"
        assert str(err) == "msg"


class TestGlobalQuotaManagement:
    def test_set_global_quota(self):
        mgr = make_manager()
        gq = mgr.set_global_quota(1000)
        assert gq.limit == 1000
        assert gq.used == 0

    def test_update_global_quota(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        gq = mgr.set_global_quota(500)
        assert gq.limit == 500

    def test_update_global_quota_truncates_used(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 1000)
        mgr.acquire("t1", 800)
        gq = mgr.set_global_quota(500)
        assert gq.used == 500

    def test_get_global_quota_not_set_raises(self):
        mgr = make_manager()
        with pytest.raises(GlobalQuotaNotSetError):
            mgr.get_global_quota()

    def test_set_global_quota_negative_raises(self):
        mgr = make_manager()
        with pytest.raises(InvalidQuotaAmountError):
            mgr.set_global_quota(-1)

    def test_get_global_quota_returns_copy(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        gq = mgr.get_global_quota()
        gq.limit = 999
        gq.used = 500
        reloaded = mgr.get_global_quota()
        assert reloaded.limit == 100
        assert reloaded.used == 0


class TestTenantManagement:
    def test_create_tenant_quota(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        tq = mgr.create_tenant_quota("tenant-1", 100)
        assert tq.tenant_id == "tenant-1"
        assert tq.limit == 100
        assert tq.used == 0

    def test_create_duplicate_tenant_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 100)
        with pytest.raises(TenantExistsError):
            mgr.create_tenant_quota("t1", 200)

    def test_create_tenant_empty_id_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            mgr.create_tenant_quota("", 100)

    def test_create_tenant_negative_limit_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        with pytest.raises(InvalidQuotaAmountError):
            mgr.create_tenant_quota("t1", -1)

    def test_get_tenant_quota_not_found_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        with pytest.raises(TenantNotFoundError):
            mgr.get_tenant_quota("nonexistent")

    def test_get_tenant_quota_returns_copy(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 100)
        tq = mgr.get_tenant_quota("t1")
        tq.limit = 999
        tq.used = 500
        reloaded = mgr.get_tenant_quota("t1")
        assert reloaded.limit == 100
        assert reloaded.used == 0

    def test_update_tenant_quota_limit(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 100)
        tq = mgr.update_tenant_quota_limit("t1", 500)
        assert tq.limit == 500

    def test_update_tenant_quota_limit_truncates_used(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 400)
        tq = mgr.update_tenant_quota_limit("t1", 200)
        assert tq.used == 200

    def test_update_tenant_quota_negative_limit_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 100)
        with pytest.raises(InvalidQuotaAmountError):
            mgr.update_tenant_quota_limit("t1", -1)

    def test_list_tenants(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("a", 100)
        mgr.create_tenant_quota("b", 200)
        tenants = mgr.list_tenants()
        assert len(tenants) == 2
        ids = {t.tenant_id for t in tenants}
        assert ids == {"a", "b"}


class TestAcquireNormalFlow:
    def test_acquire_single_tenant(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 100)
        assert mgr.get_tenant_quota("t1").used == 100
        assert mgr.get_global_quota().used == 100

    def test_acquire_multiple_times(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 100)
        mgr.acquire("t1", 200)
        assert mgr.get_tenant_quota("t1").used == 300
        assert mgr.get_global_quota().used == 300

    def test_acquire_multiple_tenants(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.create_tenant_quota("t2", 500)
        mgr.acquire("t1", 200)
        mgr.acquire("t2", 300)
        assert mgr.get_tenant_quota("t1").used == 200
        assert mgr.get_tenant_quota("t2").used == 300
        assert mgr.get_global_quota().used == 500

    def test_acquire_exact_remaining(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 100)
        mgr.acquire("t1", 100)
        assert mgr.get_tenant_quota("t1").used == 100
        assert mgr.get_tenant_quota("t1").remaining == 0
        assert mgr.get_global_quota().used == 100
        assert mgr.get_global_quota().remaining == 0


class TestAcquireQuotaLimitExceeded:
    def test_acquire_tenant_insufficient(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 50)
        mgr.acquire("t1", 50)
        with pytest.raises(QuotaLimitExceededError) as exc:
            mgr.acquire("t1", 1)
        assert exc.value.reason == "tenant_insufficient"

    def test_acquire_global_insufficient(self):
        mgr = make_manager()
        mgr.set_global_quota(50)
        mgr.create_tenant_quota("t1", 200)
        mgr.acquire("t1", 50)
        with pytest.raises(QuotaLimitExceededError) as exc:
            mgr.acquire("t1", 1)
        assert exc.value.reason == "global_insufficient"

    def test_acquire_both_insufficient(self):
        mgr = make_manager()
        mgr.set_global_quota(50)
        mgr.create_tenant_quota("t1", 50)
        mgr.acquire("t1", 50)
        with pytest.raises(QuotaLimitExceededError) as exc:
            mgr.acquire("t1", 100)
        assert exc.value.reason == "both_tenant_and_global_insufficient"

    def test_acquire_tenant_has_quota_but_global_full(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 100)
        mgr.create_tenant_quota("t2", 100)
        mgr.acquire("t1", 100)
        with pytest.raises(QuotaLimitExceededError) as exc:
            mgr.acquire("t2", 1)
        assert exc.value.reason == "global_insufficient"

    def test_acquire_global_has_quota_but_tenant_full(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 10)
        with pytest.raises(QuotaLimitExceededError) as exc:
            mgr.acquire("t1", 100)
        assert exc.value.reason == "tenant_insufficient"


class TestRelease:
    def test_release_normal(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 200)
        mgr.release("t1", 100)
        assert mgr.get_tenant_quota("t1").used == 100
        assert mgr.get_global_quota().used == 100

    def test_release_all(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 200)
        mgr.release("t1", 200)
        assert mgr.get_tenant_quota("t1").used == 0
        assert mgr.get_global_quota().used == 0

    def test_release_multiple_tenants_independent(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.create_tenant_quota("t2", 500)
        mgr.acquire("t1", 200)
        mgr.acquire("t2", 300)
        mgr.release("t1", 100)
        assert mgr.get_tenant_quota("t1").used == 100
        assert mgr.get_tenant_quota("t2").used == 300
        assert mgr.get_global_quota().used == 400

    def test_release_exceeds_tenant_used_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 100)
        with pytest.raises(ReleaseExceedUsedError):
            mgr.release("t1", 200)

    def test_release_zero_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        with pytest.raises(InvalidQuotaAmountError):
            mgr.release("t1", 0)

    def test_release_negative_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        with pytest.raises(InvalidQuotaAmountError):
            mgr.release("t1", -1)


class TestReset:
    def test_reset_tenant_quota(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.create_tenant_quota("t2", 500)
        mgr.acquire("t1", 200)
        mgr.acquire("t2", 300)
        tq = mgr.reset_tenant_quota("t1")
        assert tq.used == 0
        assert tq.reset_at is not None
        assert mgr.get_tenant_quota("t2").used == 300
        assert mgr.get_global_quota().used == 300

    def test_reset_tenant_releases_global(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 80)
        mgr.create_tenant_quota("t2", 80)
        mgr.acquire("t1", 80)
        assert mgr.get_global_quota().remaining == 20
        mgr.reset_tenant_quota("t1")
        assert mgr.get_global_quota().remaining == 100
        mgr.acquire("t2", 80)
        assert mgr.get_global_quota().used == 80

    def test_reset_global_quota(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.create_tenant_quota("t2", 500)
        mgr.acquire("t1", 200)
        mgr.acquire("t2", 300)
        gq = mgr.reset_global_quota()
        assert gq.used == 0
        assert gq.reset_at is not None
        assert mgr.get_tenant_quota("t1").used == 0
        assert mgr.get_tenant_quota("t2").used == 0
        assert mgr.get_tenant_quota("t1").reset_at is not None
        assert mgr.get_tenant_quota("t2").reset_at is not None

    def test_reset_all(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 200)
        mgr.reset_all()
        assert mgr.get_global_quota().used == 0
        assert mgr.get_tenant_quota("t1").used == 0

    def test_reset_at_critical_moment(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 100)
        mgr.acquire("t1", 100)
        with pytest.raises(QuotaLimitExceededError):
            mgr.acquire("t1", 1)
        before_reset = datetime.now()
        mgr.reset_tenant_quota("t1")
        after_reset = datetime.now()
        tq = mgr.get_tenant_quota("t1")
        assert tq.reset_at is not None
        assert before_reset <= tq.reset_at <= after_reset
        mgr.acquire("t1", 100)
        assert tq.used == 0


class TestBoundaryConditions:
    def test_tenant_quota_equals_global_quota(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 100)
        mgr.acquire("t1", 100)
        assert mgr.get_tenant_quota("t1").used == 100
        assert mgr.get_global_quota().used == 100
        with pytest.raises(QuotaLimitExceededError) as exc:
            mgr.acquire("t1", 1)
        assert exc.value.reason == "both_tenant_and_global_insufficient"

    def test_sum_of_tenant_quotas_exceeds_global(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 80)
        mgr.create_tenant_quota("t2", 80)
        mgr.acquire("t1", 80)
        with pytest.raises(QuotaLimitExceededError) as exc:
            mgr.acquire("t2", 50)
        assert exc.value.reason == "global_insufficient"

    def test_update_limit_below_used_truncates(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        mgr.acquire("t1", 400)
        mgr.update_tenant_quota_limit("t1", 200)
        assert mgr.get_tenant_quota("t1").used == 200
        assert mgr.get_tenant_quota("t1").remaining == 0

    def test_zero_limit_quota(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 0)
        with pytest.raises(QuotaLimitExceededError):
            mgr.acquire("t1", 1)

    def test_acquire_zero_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        with pytest.raises(InvalidQuotaAmountError):
            mgr.acquire("t1", 0)

    def test_acquire_negative_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 500)
        with pytest.raises(InvalidQuotaAmountError):
            mgr.acquire("t1", -1)


class TestErrorBranches:
    def test_acquire_unknown_tenant_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        with pytest.raises(TenantNotFoundError):
            mgr.acquire("nonexistent", 10)

    def test_release_unknown_tenant_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        with pytest.raises(TenantNotFoundError):
            mgr.release("nonexistent", 10)

    def test_reset_unknown_tenant_raises(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        with pytest.raises(TenantNotFoundError):
            mgr.reset_tenant_quota("nonexistent")

    def test_acquire_without_global_quota_raises(self):
        mgr = make_manager()
        mgr.create_tenant_quota("t1", 100)
        with pytest.raises(GlobalQuotaNotSetError):
            mgr.acquire("t1", 10)

    def test_release_without_global_quota_raises(self):
        mgr = make_manager()
        mgr.create_tenant_quota("t1", 100)
        with pytest.raises(GlobalQuotaNotSetError):
            mgr.release("t1", 10)

    def test_reset_tenant_without_global_quota_raises(self):
        mgr = make_manager()
        mgr.create_tenant_quota("t1", 100)
        with pytest.raises(GlobalQuotaNotSetError):
            mgr.reset_tenant_quota("t1")

    def test_reset_global_without_global_quota_raises(self):
        mgr = make_manager()
        with pytest.raises(GlobalQuotaNotSetError):
            mgr.reset_global_quota()


class TestConcurrency:
    def test_concurrent_acquire_no_overshoot(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 1000)
        errors = []

        def worker():
            for _ in range(100):
                try:
                    mgr.acquire("t1", 1)
                except QuotaLimitExceededError:
                    errors.append(1)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert mgr.get_tenant_quota("t1").used == 1000
        assert mgr.get_global_quota().used == 1000

    def test_concurrent_acquire_and_release(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 100)
        exceptions = []

        def acquirer():
            for _ in range(50):
                try:
                    mgr.acquire("t1", 1)
                except QuotaLimitExceededError:
                    pass
                except Exception as e:
                    exceptions.append(e)

        def releaser():
            for _ in range(50):
                try:
                    mgr.release("t1", 1)
                except ReleaseExceedUsedError:
                    pass
                except Exception as e:
                    exceptions.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=acquirer))
            threads.append(threading.Thread(target=releaser))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(exceptions) == 0
        assert 0 <= mgr.get_tenant_quota("t1").used <= 100
        assert 0 <= mgr.get_global_quota().used <= 100
        assert mgr.get_tenant_quota("t1").used == mgr.get_global_quota().used

    def test_concurrent_reset_and_acquire(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        mgr.create_tenant_quota("t1", 100)
        exceptions = []

        def worker_acquire():
            for _ in range(100):
                try:
                    mgr.acquire("t1", 1)
                except QuotaLimitExceededError:
                    pass
                except Exception as e:
                    exceptions.append(e)

        def worker_reset():
            for _ in range(20):
                try:
                    mgr.reset_tenant_quota("t1")
                except Exception as e:
                    exceptions.append(e)

        threads = [
            threading.Thread(target=worker_acquire),
            threading.Thread(target=worker_reset),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(exceptions) == 0
        assert mgr.get_tenant_quota("t1").used <= mgr.get_tenant_quota("t1").limit
        assert mgr.get_global_quota().used <= mgr.get_global_quota().limit


class TestEncapsulation:
    def test_tenant_quota_returned_is_copy(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 100)
        tq = mgr.get_tenant_quota("t1")
        tq.limit = 999
        tq.used = 500
        reloaded = mgr.get_tenant_quota("t1")
        assert reloaded.limit == 100
        assert reloaded.used == 0

    def test_global_quota_returned_is_copy(self):
        mgr = make_manager()
        mgr.set_global_quota(100)
        gq = mgr.get_global_quota()
        gq.limit = 999
        gq.used = 500
        reloaded = mgr.get_global_quota()
        assert reloaded.limit == 100
        assert reloaded.used == 0

    def test_list_tenants_returns_copies(self):
        mgr = make_manager()
        mgr.set_global_quota(1000)
        mgr.create_tenant_quota("t1", 100)
        tenants = mgr.list_tenants()
        tenants[0].limit = 999
        reloaded = mgr.get_tenant_quota("t1")
        assert reloaded.limit == 100
