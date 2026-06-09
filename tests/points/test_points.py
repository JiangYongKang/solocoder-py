from __future__ import annotations

import threading
from datetime import datetime, timedelta

import pytest

from solocoder_py.points import (
    AccountError,
    AccountExistsError,
    AccountNotFoundError,
    ExpiredLog,
    FreezeNotFoundError,
    FreezeStateError,
    FreezeStatus,
    FrozenRecord,
    InsufficientPointsError,
    InvalidAmountError,
    PointsAccount,
    PointsAccountManager,
    PointsBatch,
    PointsError,
    PointsExpiredError,
    make_batch,
)
from .conftest import make_manager


class TestAccountManagement:
    def test_create_account(self):
        mgr = make_manager()
        account = mgr.create_account("user-1")
        assert account.account_id == "user-1"
        assert mgr.get_available_points("user-1") == 0
        assert mgr.get_total_points("user-1") == 0

    def test_create_duplicate_account_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        with pytest.raises(AccountExistsError):
            mgr.create_account("user-1")

    def test_create_account_empty_id_raises(self):
        mgr = make_manager()
        with pytest.raises(ValueError, match="account_id cannot be empty"):
            mgr.create_account("")

    def test_get_account_not_found_raises(self):
        mgr = make_manager()
        with pytest.raises(AccountNotFoundError):
            mgr.get_account("nonexistent")

    def test_get_account_returns_copy(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        acc = mgr.get_account("user-1")
        acc.account_id = "hacked"
        reloaded = mgr.get_account("user-1")
        assert reloaded.account_id == "user-1"

    def test_list_accounts(self):
        mgr = make_manager()
        mgr.create_account("a")
        mgr.create_account("b")
        accounts = mgr.list_accounts()
        assert len(accounts) == 2
        ids = {a.account_id for a in accounts}
        assert ids == {"a", "b"}


class TestAddPoints:
    def test_add_points_single_batch(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        future = datetime.now() + timedelta(days=30)
        batch = mgr.add_points("user-1", 100, future)
        assert batch.total_points == 100
        assert batch.remaining_points == 100
        assert mgr.get_available_points("user-1") == 100
        assert mgr.get_total_points("user-1") == 100

    def test_add_points_multiple_batches(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=30))
        mgr.add_points("user-1", 200, now + timedelta(days=60))
        assert mgr.get_available_points("user-1") == 300
        assert mgr.get_total_points("user-1") == 300

    def test_add_points_negative_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        with pytest.raises(InvalidAmountError):
            mgr.add_points("user-1", -10, datetime.now() + timedelta(days=1))

    def test_add_points_zero_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        with pytest.raises(InvalidAmountError):
            mgr.add_points("user-1", 0, datetime.now() + timedelta(days=1))

    def test_add_points_account_not_found_raises(self):
        mgr = make_manager()
        with pytest.raises(AccountNotFoundError):
            mgr.add_points("nonexistent", 100, datetime.now() + timedelta(days=1))

    def test_add_points_batch_returns_copy(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        batch = mgr.add_points("user-1", 100, datetime.now() + timedelta(days=1))
        batch.remaining_points = 9999
        batches = mgr.get_batches("user-1")
        assert batches[0].remaining_points == 100


class TestAvailablePointsCalculation:
    def test_expired_batch_not_counted_in_available(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        past = now - timedelta(days=1)
        future = now + timedelta(days=30)
        mgr.add_points("user-1", 100, past)
        mgr.add_points("user-1", 200, future)
        assert mgr.get_available_points("user-1") == 200
        assert mgr.get_total_points("user-1") == 300

    def test_expired_at_exact_boundary(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now)
        assert mgr.get_available_points("user-1") == 0


class TestConsumePointsFEFO:
    def test_consume_single_batch(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        batch = mgr.add_points("user-1", 100, now + timedelta(days=30))
        deductions = mgr.consume_points("user-1", 40)
        assert deductions == {batch.batch_id: 40}
        assert mgr.get_available_points("user-1") == 60

    def test_consume_fefo_multiple_batches(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        batch_early = mgr.add_points("user-1", 100, now + timedelta(days=10))
        batch_late = mgr.add_points("user-1", 200, now + timedelta(days=30))

        deductions = mgr.consume_points("user-1", 150)
        assert deductions[batch_early.batch_id] == 100
        assert deductions[batch_late.batch_id] == 50
        assert mgr.get_available_points("user-1") == 150

        batches = mgr.get_batches("user-1")
        by_id = {b.batch_id: b for b in batches}
        assert by_id[batch_early.batch_id].remaining_points == 0
        assert by_id[batch_late.batch_id].remaining_points == 150

    def test_consume_exact_batch_total(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        batch1 = mgr.add_points("user-1", 100, now + timedelta(days=10))
        batch2 = mgr.add_points("user-1", 100, now + timedelta(days=20))

        deductions = mgr.consume_points("user-1", 100)
        assert deductions == {batch1.batch_id: 100}

        deductions = mgr.consume_points("user-1", 100)
        assert deductions == {batch2.batch_id: 100}

        assert mgr.get_available_points("user-1") == 0

    def test_consume_insufficient_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 50, now + timedelta(days=30))
        with pytest.raises(InsufficientPointsError):
            mgr.consume_points("user-1", 100)

    def test_consume_expired_points_raises_points_expired_error(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        assert mgr.get_available_points("user-1") == 0
        assert mgr.get_total_points("user-1") == 100
        with pytest.raises(PointsExpiredError):
            mgr.consume_points("user-1", 10)

    def test_consume_mixed_expired_and_valid(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        mgr.add_points("user-1", 50, now + timedelta(days=10))

        deductions = mgr.consume_points("user-1", 30)
        assert sum(deductions.values()) == 30
        assert mgr.get_available_points("user-1") == 20

    def test_consume_negative_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        with pytest.raises(InvalidAmountError):
            mgr.consume_points("user-1", -10)

    def test_consume_zero_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        with pytest.raises(InvalidAmountError):
            mgr.consume_points("user-1", 0)

    def test_consume_at_expiry_boundary(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        t0 = datetime.now()
        expiry = t0 + timedelta(seconds=10)
        mgr.add_points("user-1", 100, expiry)

        deductions = mgr.consume_points("user-1", 50, now=t0 + timedelta(seconds=5))
        assert sum(deductions.values()) == 50
        assert mgr.get_available_points("user-1", now=t0 + timedelta(seconds=5)) == 50

        with pytest.raises(PointsExpiredError):
            mgr.consume_points("user-1", 50, now=expiry + timedelta(seconds=1))


class TestFreezeAndUnfreeze:
    def test_freeze_points(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        batch = mgr.add_points("user-1", 100, now + timedelta(days=30))

        record = mgr.freeze_points("user-1", 40)
        assert record.is_frozen is True
        assert record.total_amount == 40
        assert record.batch_deductions == {batch.batch_id: 40}
        assert mgr.get_available_points("user-1") == 60
        assert mgr.get_frozen_points("user-1") == 40
        assert mgr.get_total_points("user-1") == 100

    def test_freeze_fefo_multiple_batches(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        b1 = mgr.add_points("user-1", 50, now + timedelta(days=10))
        b2 = mgr.add_points("user-1", 100, now + timedelta(days=30))

        record = mgr.freeze_points("user-1", 80)
        assert record.batch_deductions[b1.batch_id] == 50
        assert record.batch_deductions[b2.batch_id] == 30
        assert mgr.get_available_points("user-1") == 70
        assert mgr.get_frozen_points("user-1") == 80

    def test_freeze_insufficient_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 50, now + timedelta(days=10))
        with pytest.raises(InsufficientPointsError):
            mgr.freeze_points("user-1", 100)

    def test_unfreeze_points(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=30))

        record = mgr.freeze_points("user-1", 40)
        assert mgr.get_available_points("user-1") == 60
        assert mgr.get_frozen_points("user-1") == 40

        unfrozen = mgr.unfreeze_points(record.freeze_id)
        assert unfrozen.is_unfrozen is True
        assert mgr.get_available_points("user-1") == 100
        assert mgr.get_frozen_points("user-1") == 0

    def test_unfreeze_already_unfrozen_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=30))
        record = mgr.freeze_points("user-1", 40)
        mgr.unfreeze_points(record.freeze_id)
        with pytest.raises(FreezeStateError):
            mgr.unfreeze_points(record.freeze_id)

    def test_consume_frozen_points(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=30))

        record = mgr.freeze_points("user-1", 40)
        consumed = mgr.consume_frozen_points(record.freeze_id)
        assert consumed.is_consumed is True
        assert mgr.get_available_points("user-1") == 60
        assert mgr.get_frozen_points("user-1") == 0
        assert mgr.get_total_points("user-1") == 60

    def test_consume_already_consumed_frozen_raises(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=30))
        record = mgr.freeze_points("user-1", 40)
        mgr.consume_frozen_points(record.freeze_id)
        with pytest.raises(FreezeStateError):
            mgr.consume_frozen_points(record.freeze_id)

    def test_freeze_not_found_raises(self):
        mgr = make_manager()
        with pytest.raises(FreezeNotFoundError):
            mgr.get_frozen_record("nonexistent")

    def test_get_frozen_record_returns_copy(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=30))
        record = mgr.freeze_points("user-1", 40)

        loaded = mgr.get_frozen_record(record.freeze_id)
        loaded.total_amount = 9999
        reloaded = mgr.get_frozen_record(record.freeze_id)
        assert reloaded.total_amount == 40


class TestExpiredPointsRecycling:
    def test_recycle_specific_account(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        mgr.create_account("user-2")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        mgr.add_points("user-2", 200, now - timedelta(days=1))

        logs = mgr.recycle_expired_points("user-1")
        assert len(logs) == 1
        assert logs[0].account_id == "user-1"
        assert logs[0].recycled_points == 100
        assert mgr.get_total_points("user-1") == 0
        assert mgr.get_total_points("user-2") == 200

    def test_recycle_all_accounts(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        mgr.create_account("user-2")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        mgr.add_points("user-2", 200, now - timedelta(days=1))

        logs = mgr.recycle_expired_points()
        assert len(logs) == 2
        total_recycled = sum(l.recycled_points for l in logs)
        assert total_recycled == 300
        assert mgr.get_total_points("user-1") == 0
        assert mgr.get_total_points("user-2") == 0

    def test_recycle_only_remaining_points(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        batch = mgr.add_points("user-1", 100, now + timedelta(days=10))
        mgr.consume_points("user-1", 30)

        future_recycle_time = now + timedelta(days=20)
        logs = mgr.recycle_expired_points("user-1", now=future_recycle_time)
        assert len(logs) == 1
        assert logs[0].recycled_points == 70
        assert logs[0].batch_id == batch.batch_id

    def test_recycle_does_not_affect_frozen_points(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=10))
        mgr.freeze_points("user-1", 40)

        future_recycle_time = now + timedelta(days=20)
        logs = mgr.recycle_expired_points("user-1", now=future_recycle_time)
        assert len(logs) == 1
        assert logs[0].recycled_points == 60
        assert mgr.get_frozen_points("user-1") == 40
        assert mgr.get_total_points("user-1") == 40

    def test_recycle_idempotent(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))

        logs1 = mgr.recycle_expired_points("user-1")
        assert len(logs1) == 1

        logs2 = mgr.recycle_expired_points("user-1")
        assert len(logs2) == 0

        all_logs = mgr.get_expired_logs("user-1")
        assert len(all_logs) == 1

    def test_recycle_logs_are_recorded(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        mgr.add_points("user-1", 200, now - timedelta(days=2))

        mgr.recycle_expired_points("user-1")
        logs = mgr.get_expired_logs("user-1")
        assert len(logs) == 2
        for log in logs:
            assert isinstance(log, ExpiredLog)
            assert log.account_id == "user-1"


class TestModels:
    def test_points_batch_is_expired(self):
        now = datetime.now()
        batch = make_batch("acc-1", 100, now + timedelta(days=1))
        assert batch.is_expired(now) is False
        assert batch.is_expired(now + timedelta(days=2)) is True
        assert batch.is_expired(now + timedelta(days=1)) is True

    def test_points_batch_copy_is_independent(self):
        now = datetime.now()
        batch = make_batch("acc-1", 100, now + timedelta(days=1))
        dup = batch.copy()
        dup.remaining_points = 9999
        assert batch.remaining_points == 100

    def test_frozen_record_state_transitions(self):
        now = datetime.now()
        record = FrozenRecord(
            freeze_id="f-1",
            account_id="acc-1",
            total_amount=100,
            status=FreezeStatus.FROZEN,
            created_at=now,
        )
        assert record.is_frozen is True
        assert record.is_consumed is False
        assert record.is_unfrozen is False

        record.mark_consumed()
        assert record.is_consumed is True
        assert record.is_frozen is False

    def test_frozen_record_mark_consumed_wrong_state_raises_freeze_state_error(self):
        now = datetime.now()
        record = FrozenRecord(
            freeze_id="f-1",
            account_id="acc-1",
            total_amount=100,
            status=FreezeStatus.CONSUMED,
            created_at=now,
        )
        with pytest.raises(FreezeStateError):
            record.mark_consumed()

    def test_frozen_record_mark_unfrozen_wrong_state_raises_freeze_state_error(self):
        now = datetime.now()
        record = FrozenRecord(
            freeze_id="f-1",
            account_id="acc-1",
            total_amount=100,
            status=FreezeStatus.UNFROZEN,
            created_at=now,
        )
        with pytest.raises(FreezeStateError):
            record.mark_unfrozen()

    def test_frozen_record_copy_is_independent(self):
        now = datetime.now()
        record = FrozenRecord(
            freeze_id="f-1",
            account_id="acc-1",
            total_amount=100,
            status=FreezeStatus.FROZEN,
            created_at=now,
            batch_deductions={"b-1": 50, "b-2": 50},
        )
        dup = record.copy()
        dup.batch_deductions["b-1"] = 9999
        assert record.batch_deductions["b-1"] == 50

    def test_points_batch_validation(self):
        now = datetime.now()
        with pytest.raises(InvalidAmountError):
            PointsBatch(
                batch_id="b-1",
                account_id="acc-1",
                total_points=100,
                remaining_points=60,
                frozen_points=50,
                created_at=now,
                expired_at=now + timedelta(days=1),
            )


class TestExceptionHierarchy:
    def test_all_account_errors_inherit_from_points_error(self):
        assert issubclass(AccountNotFoundError, PointsError)
        assert issubclass(AccountExistsError, PointsError)
        assert issubclass(InsufficientPointsError, PointsError)
        assert issubclass(InvalidAmountError, PointsError)
        assert issubclass(FreezeNotFoundError, PointsError)
        assert issubclass(FreezeStateError, PointsError)
        assert issubclass(PointsExpiredError, PointsError)

    def test_all_account_errors_inherit_from_account_error(self):
        assert issubclass(AccountNotFoundError, AccountError)
        assert issubclass(AccountExistsError, AccountError)
        assert issubclass(InsufficientPointsError, AccountError)
        assert issubclass(PointsExpiredError, AccountError)
        assert issubclass(FreezeStateError, AccountError)


class TestEdgeCases:
    def test_consume_points_crossing_expiry_boundary(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        t0 = datetime.now()
        expiry = t0 + timedelta(seconds=100)
        batch = mgr.add_points("user-1", 100, expiry)

        t_before = t0 + timedelta(seconds=50)
        deductions_before = mgr.consume_points("user-1", 30, now=t_before)
        assert deductions_before == {batch.batch_id: 30}
        assert mgr.get_available_points("user-1", now=t_before) == 70

        t_after = t0 + timedelta(seconds=200)
        with pytest.raises(PointsExpiredError):
            mgr.consume_points("user-1", 70, now=t_after)

        assert mgr.get_available_points("user-1", now=t_after) == 0

    def test_many_batches_fefo_ordering(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()

        batch_ids_expiry = []
        for days in [30, 5, 20, 10, 15]:
            b = mgr.add_points("user-1", 10, now + timedelta(days=days))
            batch_ids_expiry.append((b.batch_id, days))

        expected_order = sorted(batch_ids_expiry, key=lambda x: x[1])
        deductions = mgr.consume_points("user-1", 25)

        deduct_order = list(deductions.keys())
        assert deduct_order == [bid for bid, _ in expected_order[:3]]
        assert deductions[expected_order[0][0]] == 10
        assert deductions[expected_order[1][0]] == 10
        assert deductions[expected_order[2][0]] == 5

    def test_unfreeze_restores_to_original_batches(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        b1 = mgr.add_points("user-1", 50, now + timedelta(days=10))
        b2 = mgr.add_points("user-1", 100, now + timedelta(days=30))

        record = mgr.freeze_points("user-1", 80)
        assert record.batch_deductions[b1.batch_id] == 50
        assert record.batch_deductions[b2.batch_id] == 30

        mgr.unfreeze_points(record.freeze_id)

        batches = mgr.get_batches("user-1")
        by_id = {b.batch_id: b for b in batches}
        assert by_id[b1.batch_id].remaining_points == 50
        assert by_id[b1.batch_id].frozen_points == 0
        assert by_id[b2.batch_id].remaining_points == 100
        assert by_id[b2.batch_id].frozen_points == 0

    def test_freeze_expired_points_raises_points_expired_error(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        assert mgr.get_total_points("user-1") == 100
        with pytest.raises(PointsExpiredError):
            mgr.freeze_points("user-1", 10)

    def test_get_batches_returns_copies(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=1))

        batches = mgr.get_batches("user-1")
        batches[0].remaining_points = 9999
        reloaded = mgr.get_batches("user-1")
        assert reloaded[0].remaining_points == 100


class TestConcurrency:
    def test_concurrent_consume_no_overdraft(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=30))

        success_count = {"count": 0}
        overdraft_count = {"count": 0}
        lock = threading.Lock()

        def try_consume():
            for _ in range(20):
                try:
                    mgr.consume_points("user-1", 3)
                    with lock:
                        success_count["count"] += 1
                except InsufficientPointsError:
                    with lock:
                        overdraft_count["count"] += 1

        threads = [threading.Thread(target=try_consume) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            assert t.is_alive() is False

        total_consumed = success_count["count"] * 3
        assert total_consumed <= 100
        assert mgr.get_total_points("user-1") == 100 - total_consumed
        assert success_count["count"] + overdraft_count["count"] == 100

    def test_concurrent_add_and_consume(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        base_time = datetime.now()

        errors = []
        lock = threading.Lock()

        def add_points_task():
            try:
                for i in range(10):
                    mgr.add_points(
                        "user-1", 10, base_time + timedelta(days=30 + i)
                    )
            except Exception as e:
                with lock:
                    errors.append(e)

        def consume_points_task():
            try:
                for _ in range(10):
                    try:
                        mgr.consume_points("user-1", 5)
                    except InsufficientPointsError:
                        pass
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [
            threading.Thread(target=add_points_task),
            threading.Thread(target=consume_points_task),
            threading.Thread(target=add_points_task),
            threading.Thread(target=consume_points_task),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            assert t.is_alive() is False

        assert len(errors) == 0
        total = mgr.get_total_points("user-1")
        available = mgr.get_available_points("user-1")
        assert available <= total


class TestPointsExpiredErrorScenarios:
    def test_consume_partial_expired_partial_valid_uses_valid_only(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        mgr.add_points("user-1", 50, now + timedelta(days=10))

        assert mgr.get_total_points("user-1") == 150
        assert mgr.get_available_points("user-1") == 50

        with pytest.raises(PointsExpiredError):
            mgr.consume_points("user-1", 80)

        deductions = mgr.consume_points("user-1", 50)
        assert sum(deductions.values()) == 50
        assert mgr.get_available_points("user-1") == 0

    def test_freeze_partial_expired_partial_valid(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        mgr.add_points("user-1", 50, now + timedelta(days=10))

        assert mgr.get_total_points("user-1") == 150
        assert mgr.get_available_points("user-1") == 50

        with pytest.raises(PointsExpiredError):
            mgr.freeze_points("user-1", 80)

        record = mgr.freeze_points("user-1", 30)
        assert record.total_amount == 30
        assert mgr.get_frozen_points("user-1") == 30
        assert mgr.get_available_points("user-1") == 20

    def test_consume_all_expired_raises_expired_not_insufficient(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now - timedelta(days=1))
        mgr.add_points("user-1", 200, now - timedelta(days=2))

        assert mgr.get_total_points("user-1") == 300
        assert mgr.get_available_points("user-1") == 0

        with pytest.raises(PointsExpiredError):
            mgr.consume_points("user-1", 100)

        with pytest.raises(InsufficientPointsError):
            mgr.consume_points("user-1", 400)

    def test_points_expired_error_is_distinct_from_insufficient(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        now = datetime.now()
        mgr.add_points("user-1", 100, now + timedelta(days=10))

        with pytest.raises(InsufficientPointsError):
            mgr.consume_points("user-1", 200)

        mgr2 = make_manager()
        mgr2.create_account("user-2")
        mgr2.add_points("user-2", 500, now - timedelta(days=1))
        with pytest.raises(PointsExpiredError):
            mgr2.consume_points("user-2", 200)


class TestUnfreezeWithExpiredBatches:
    def test_unfreeze_after_batch_expired_recycles_points(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        t0 = datetime.now()
        batch = mgr.add_points("user-1", 100, t0 + timedelta(days=10))

        record = mgr.freeze_points("user-1", 80, now=t0)
        assert mgr.get_available_points("user-1", now=t0) == 20
        assert mgr.get_frozen_points("user-1") == 80
        assert mgr.get_total_points("user-1") == 100

        t_after = t0 + timedelta(days=20)
        unfrozen = mgr.unfreeze_points(record.freeze_id, now=t_after)
        assert unfrozen.is_unfrozen is True

        assert mgr.get_frozen_points("user-1") == 0
        assert mgr.get_available_points("user-1", now=t_after) == 0
        assert mgr.get_total_points("user-1") == 20

        logs = mgr.get_expired_logs("user-1")
        assert len(logs) == 1
        assert logs[0].batch_id == batch.batch_id
        assert logs[0].recycled_points == 80

    def test_unfreeze_partial_expired_partial_valid(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        t0 = datetime.now()
        b1 = mgr.add_points("user-1", 50, t0 + timedelta(days=5))
        b2 = mgr.add_points("user-1", 100, t0 + timedelta(days=30))

        record = mgr.freeze_points("user-1", 80, now=t0)
        assert record.batch_deductions[b1.batch_id] == 50
        assert record.batch_deductions[b2.batch_id] == 30
        assert mgr.get_frozen_points("user-1") == 80
        assert mgr.get_available_points("user-1", now=t0) == 70

        t_mid = t0 + timedelta(days=15)
        unfrozen = mgr.unfreeze_points(record.freeze_id, now=t_mid)
        assert unfrozen.is_unfrozen is True

        assert mgr.get_frozen_points("user-1") == 0
        assert mgr.get_available_points("user-1", now=t_mid) == 100
        assert mgr.get_total_points("user-1") == 100

        batches = mgr.get_batches("user-1")
        by_id = {b.batch_id: b for b in batches}
        assert by_id[b1.batch_id].remaining_points == 0
        assert by_id[b1.batch_id].frozen_points == 0
        assert by_id[b1.batch_id].total_points == 50
        assert by_id[b2.batch_id].remaining_points == 100
        assert by_id[b2.batch_id].frozen_points == 0
        assert by_id[b2.batch_id].total_points == 100

        logs = mgr.get_expired_logs("user-1")
        assert len(logs) == 1
        assert logs[0].batch_id == b1.batch_id
        assert logs[0].recycled_points == 50

    def test_unfreeze_before_expiry_restores_normally(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        t0 = datetime.now()
        mgr.add_points("user-1", 100, t0 + timedelta(days=30))

        record = mgr.freeze_points("user-1", 60, now=t0)
        assert mgr.get_available_points("user-1", now=t0) == 40
        assert mgr.get_frozen_points("user-1") == 60

        t_early = t0 + timedelta(days=5)
        unfrozen = mgr.unfreeze_points(record.freeze_id, now=t_early)
        assert unfrozen.is_unfrozen is True

        assert mgr.get_available_points("user-1", now=t_early) == 100
        assert mgr.get_frozen_points("user-1") == 0
        assert mgr.get_total_points("user-1") == 100

        logs = mgr.get_expired_logs("user-1")
        assert len(logs) == 0

    def test_unfreeze_expired_batch_then_consume_restricted(self):
        mgr = make_manager()
        mgr.create_account("user-1")
        t0 = datetime.now()
        mgr.add_points("user-1", 100, t0 + timedelta(days=5))

        record = mgr.freeze_points("user-1", 80, now=t0)

        t_after = t0 + timedelta(days=10)
        mgr.unfreeze_points(record.freeze_id, now=t_after)

        assert mgr.get_available_points("user-1", now=t_after) == 0
        assert mgr.get_total_points("user-1") == 20

        with pytest.raises(PointsExpiredError):
            mgr.consume_points("user-1", 10, now=t_after)

