from datetime import timedelta
from time import sleep

import pytest

from solocoder_py.lock import (
    DistributedLockManager,
    InvalidFenceTokenError,
    LockAcquisitionTimeoutError,
    LockEntry,
    LockExpiredError,
    LockNotAcquiredError,
    LockNotHeldError,
    LockState,
)
from .conftest import make_manager


class TestLockEntryModel:
    def test_lock_entry_creation(self):
        entry = LockEntry(lock_name="test-lock")
        assert entry.lock_name == "test-lock"
        assert entry.state == LockState.FREE
        assert entry.client_id is None
        assert entry.fence_token == 0
        assert entry.reentrant_count == 0
        assert entry.lease_expires_at is None
        assert entry.is_held is False
        assert entry.is_expired is False

    def test_lock_entry_empty_name_rejected(self):
        with pytest.raises(ValueError, match="lock_name cannot be empty"):
            LockEntry(lock_name="")

    def test_lock_entry_negative_reentrant_count_rejected(self):
        with pytest.raises(ValueError, match="reentrant_count cannot be negative"):
            LockEntry(lock_name="test", reentrant_count=-1)

    def test_lock_entry_negative_fence_token_rejected(self):
        with pytest.raises(ValueError, match="fence_token cannot be negative"):
            LockEntry(lock_name="test", fence_token=-1)

    def test_lock_entry_acquire(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=30))
        assert entry.state == LockState.HELD
        assert entry.client_id == "client-1"
        assert entry.fence_token == 1
        assert entry.reentrant_count == 1
        assert entry.is_held is True
        assert entry.is_held_by("client-1") is True
        assert entry.is_held_by("client-2") is False

    def test_lock_entry_reenter(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=30))
        entry.reenter()
        assert entry.reentrant_count == 2
        assert entry.is_held is True

    def test_lock_entry_release_one_reentrant(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=30))
        entry.reenter()
        entry.reenter()
        assert entry.reentrant_count == 3

        fully_released = entry.release_one()
        assert fully_released is False
        assert entry.reentrant_count == 2
        assert entry.is_held is True

        fully_released = entry.release_one()
        assert fully_released is False
        assert entry.reentrant_count == 1
        assert entry.is_held is True

        fully_released = entry.release_one()
        assert fully_released is True
        assert entry.reentrant_count == 0
        assert entry.state == LockState.FREE
        assert entry.is_held is False

    def test_lock_entry_force_release(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=30))
        entry.reenter()
        entry.force_release()
        assert entry.state == LockState.FREE
        assert entry.client_id is None
        assert entry.reentrant_count == 0
        assert entry.is_held is False

    def test_lock_entry_renew(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=1))
        original_expiry = entry.lease_expires_at
        sleep(0.05)
        entry.renew(timedelta(seconds=60))
        assert entry.lease_expires_at > original_expiry
        assert entry.lease_duration == timedelta(seconds=60)

    def test_lock_entry_is_expired(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(milliseconds=50))
        assert entry.is_expired is False
        sleep(0.1)
        assert entry.is_expired is True
        assert entry.is_held is False

    def test_lock_entry_remaining_lease(self):
        entry = LockEntry(lock_name="test-lock")
        assert entry.remaining_lease is None
        entry.acquire("client-1", 1, timedelta(seconds=30))
        remaining = entry.remaining_lease
        assert remaining is not None
        assert remaining.total_seconds() > 0
        assert remaining.total_seconds() <= 30

    def test_lock_entry_reenter_explicit_zero_duration_not_fallback(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=30))
        entry.reenter(lease_duration=timedelta(seconds=0))
        assert entry.lease_duration == timedelta(seconds=0)
        assert entry.reentrant_count == 2

    def test_lock_entry_renew_explicit_zero_duration_not_fallback(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=30))
        entry.renew(lease_duration=timedelta(seconds=0))
        assert entry.lease_duration == timedelta(seconds=0)

    def test_lock_entry_release_one_defensive_no_negative_count(self):
        entry = LockEntry(lock_name="test-lock")
        entry.acquire("client-1", 1, timedelta(seconds=30))
        assert entry.reentrant_count == 1
        fully = entry.release_one()
        assert fully is True
        assert entry.reentrant_count == 0
        assert entry.state == LockState.FREE
        entry.acquire("client-1", 1, timedelta(seconds=30))
        entry.reenter()
        entry.reenter()
        assert entry.reentrant_count == 3
        fully = entry.release_one()
        assert fully is False
        assert entry.reentrant_count == 2
        fully = entry.release_one()
        assert fully is False
        assert entry.reentrant_count == 1
        fully = entry.release_one()
        assert fully is True
        assert entry.reentrant_count == 0


class TestAcquireLock:
    def test_acquire_free_lock(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        assert token > 0
        assert manager.is_held("lock-1") is True
        assert manager.is_held_by("lock-1", "client-1") is True

    def test_acquire_returns_monotonic_increasing_tokens(self):
        manager = make_manager()
        token1 = manager.acquire("lock-1", "client-1")
        manager.release("lock-1", "client-1", token1)
        token2 = manager.acquire("lock-2", "client-1")
        token3 = manager.acquire("lock-1", "client-2")
        assert token2 > token1
        assert token3 > token2

    def test_acquire_held_by_other_fails(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        with pytest.raises(LockNotAcquiredError):
            manager.acquire("lock-1", "client-2")

    def test_try_acquire_held_by_other_returns_none(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        result = manager.try_acquire("lock-1", "client-2")
        assert result is None

    def test_try_acquire_free_lock_returns_token(self):
        manager = make_manager()
        token = manager.try_acquire("lock-1", "client-1")
        assert token is not None
        assert token > 0

    def test_acquire_with_timeout_waits_then_succeeds(self):
        manager = make_manager()
        token1 = manager.acquire("lock-1", "client-1", lease_duration=timedelta(milliseconds=100))

        import threading

        result = {}

        def acquire_in_thread():
            result["token"] = manager.acquire(
                "lock-1", "client-2", timeout=timedelta(seconds=2)
            )

        t = threading.Thread(target=acquire_in_thread)
        t.start()
        t.join(timeout=5)
        assert t.is_alive() is False
        assert "token" in result
        assert result["token"] > token1

    def test_acquire_with_timeout_raises_on_timeout(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        with pytest.raises(LockAcquisitionTimeoutError):
            manager.acquire(
                "lock-1", "client-2",
                timeout=timedelta(milliseconds=50),
                retry_interval=timedelta(milliseconds=10),
            )

    def test_acquire_empty_lock_name_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="lock_name cannot be empty"):
            manager.acquire("", "client-1")

    def test_acquire_empty_client_id_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="client_id cannot be empty"):
            manager.acquire("lock-1", "")

    def test_acquire_zero_lease_duration_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="lease_duration must be positive"):
            manager.acquire("lock-1", "client-1", lease_duration=timedelta(seconds=0))

    def test_acquire_negative_timeout_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="timeout must be positive"):
            manager.acquire("lock-1", "client-1", timeout=timedelta(seconds=-1))

    def test_acquire_with_custom_lease_duration(self):
        manager = make_manager()
        manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(seconds=60)
        )
        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.lease_duration == timedelta(seconds=60)
        remaining = info.remaining_lease
        assert remaining is not None
        assert remaining.total_seconds() > 50


class TestReleaseLock:
    def test_release_held_lock(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        fully_released = manager.release("lock-1", "client-1", token)
        assert fully_released is True
        assert manager.is_held("lock-1") is False

    def test_release_with_wrong_token_rejected(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        with pytest.raises(InvalidFenceTokenError):
            manager.release("lock-1", "client-1", 999)

    def test_release_with_wrong_client_rejected(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        with pytest.raises(LockNotHeldError):
            manager.release("lock-1", "client-2", token)

    def test_release_free_lock_rejected(self):
        manager = make_manager()
        with pytest.raises(LockNotHeldError):
            manager.release("lock-1", "client-1", 1)

    def test_release_empty_lock_name_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="lock_name cannot be empty"):
            manager.release("", "client-1", 1)

    def test_release_empty_client_id_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="client_id cannot be empty"):
            manager.release("lock-1", "", 1)

    def test_release_zero_fence_token_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="fence_token must be positive"):
            manager.release("lock-1", "client-1", 0)


class TestRenewLease:
    def test_renew_held_lock(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(seconds=1)
        )
        sleep(0.05)
        original_info = manager.get_lock_info("lock-1")
        assert original_info is not None
        original_expiry = original_info.lease_expires_at

        renewed = manager.renew(
            "lock-1", "client-1", token, lease_duration=timedelta(seconds=60)
        )
        assert renewed == timedelta(seconds=60)

        new_info = manager.get_lock_info("lock-1")
        assert new_info is not None
        assert new_info.lease_expires_at > original_expiry
        remaining = new_info.remaining_lease
        assert remaining is not None
        assert remaining.total_seconds() > 50

    def test_renew_with_default_duration(self):
        manager = make_manager(default_lease_duration=timedelta(seconds=45))
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(seconds=1)
        )
        renewed = manager.renew("lock-1", "client-1", token)
        assert renewed == timedelta(seconds=45)

    def test_renew_with_wrong_token_rejected(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        with pytest.raises(InvalidFenceTokenError):
            manager.renew("lock-1", "client-1", 999)

    def test_renew_with_wrong_client_rejected(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        with pytest.raises(LockNotHeldError):
            manager.renew("lock-1", "client-2", token)

    def test_renew_free_lock_rejected(self):
        manager = make_manager()
        with pytest.raises(LockNotHeldError):
            manager.renew("lock-1", "client-1", 1)

    def test_renew_expired_lock_rejected(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        with pytest.raises(LockExpiredError):
            manager.renew("lock-1", "client-1", token)

    def test_renew_empty_lock_name_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="lock_name cannot be empty"):
            manager.renew("", "client-1", 1)

    def test_renew_empty_client_id_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="client_id cannot be empty"):
            manager.renew("lock-1", "", 1)

    def test_renew_zero_fence_token_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="fence_token must be positive"):
            manager.renew("lock-1", "client-1", 0)

    def test_renew_zero_lease_duration_rejected(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        with pytest.raises(ValueError, match="lease_duration must be positive"):
            manager.renew("lock-1", "client-1", token, lease_duration=timedelta(seconds=0))


class TestReentrantLock:
    def test_same_client_reenters_lock(self):
        manager = make_manager()
        token1 = manager.acquire("lock-1", "client-1")
        token2 = manager.acquire("lock-1", "client-1")
        token3 = manager.acquire("lock-1", "client-1")

        assert token1 == token2 == token3

        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.reentrant_count == 3

    def test_reentrant_release_one_by_one(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        manager.acquire("lock-1", "client-1")
        manager.acquire("lock-1", "client-1")

        fully_released = manager.release("lock-1", "client-1", token)
        assert fully_released is False
        assert manager.is_held("lock-1") is True

        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.reentrant_count == 2

        fully_released = manager.release("lock-1", "client-1", token)
        assert fully_released is False
        assert manager.is_held("lock-1") is True

        fully_released = manager.release("lock-1", "client-1", token)
        assert fully_released is True
        assert manager.is_held("lock-1") is False

    def test_reentrant_other_client_blocked(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        manager.acquire("lock-1", "client-1")
        with pytest.raises(LockNotAcquiredError):
            manager.acquire("lock-1", "client-2")

    def test_reentrant_renew_extends_lease(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=100)
        )
        manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(seconds=60)
        )
        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.lease_duration == timedelta(seconds=60)
        remaining = info.remaining_lease
        assert remaining is not None
        assert remaining.total_seconds() > 50
        assert info.reentrant_count == 2


class TestLeaseExpiration:
    def test_lock_auto_expires_after_lease(self):
        manager = make_manager()
        manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        assert manager.is_held("lock-1") is True
        sleep(0.1)
        assert manager.is_held("lock-1") is False

    def test_expired_lock_can_be_acquired_by_another_client(self):
        manager = make_manager()
        token1 = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        token2 = manager.acquire("lock-1", "client-2")
        assert token2 > token1
        assert manager.is_held_by("lock-1", "client-2") is True
        assert manager.is_held_by("lock-1", "client-1") is False

    def test_release_expired_lock_raises(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        with pytest.raises(LockExpiredError):
            manager.release("lock-1", "client-1", token)

    def test_release_expired_lock_preserves_metadata_no_side_effect(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        with pytest.raises(LockExpiredError):
            manager.release("lock-1", "client-1", token)
        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.state == LockState.EXPIRED
        assert info.client_id == "client-1"
        assert info.fence_token == token
        assert info.reentrant_count == 1

    def test_renew_expired_lock_preserves_metadata_no_side_effect(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        with pytest.raises(LockExpiredError):
            manager.renew("lock-1", "client-1", token)
        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.state == LockState.EXPIRED
        assert info.client_id == "client-1"
        assert info.fence_token == token
        assert info.reentrant_count == 1

    def test_release_expired_with_wrong_token_raises_invalid_token(self):
        manager = make_manager()
        manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        with pytest.raises(InvalidFenceTokenError):
            manager.release("lock-1", "client-1", 9999)

    def test_release_expired_with_wrong_client_raises_not_held(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        with pytest.raises(LockNotHeldError):
            manager.release("lock-1", "client-2", token)

    def test_original_holder_cannot_release_after_new_holder_acquired(self):
        manager = make_manager()
        token1 = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        token2 = manager.acquire("lock-1", "client-2")

        with pytest.raises(InvalidFenceTokenError):
            manager.release("lock-1", "client-1", token1)

        assert manager.is_held_by("lock-1", "client-2") is True
        manager.release("lock-1", "client-2", token2)
        assert manager.is_held("lock-1") is False


class TestFenceTokenMechanism:
    def test_fence_tokens_are_monotonic(self):
        manager = make_manager()
        tokens = []
        for i in range(5):
            t = manager.acquire(f"lock-{i}", f"client-{i}")
            tokens.append(t)
            manager.release(f"lock-{i}", f"client-{i}", t)
        for i in range(1, len(tokens)):
            assert tokens[i] > tokens[i - 1]

    def test_new_holder_gets_higher_token(self):
        manager = make_manager()
        token1 = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        token2 = manager.acquire("lock-1", "client-2")
        assert token2 > token1

    def test_validate_fence_token_for_current_holder(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        assert manager.validate_fence_token("lock-1", token) is True

    def test_validate_fence_token_for_old_holder_after_new_acquire(self):
        manager = make_manager()
        token1 = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        token2 = manager.acquire("lock-1", "client-2")
        assert manager.validate_fence_token("lock-1", token1) is False
        assert manager.validate_fence_token("lock-1", token2) is True

    def test_validate_fence_token_for_free_lock(self):
        manager = make_manager()
        assert manager.validate_fence_token("lock-1", 1) is False

    def test_fence_token_write_operation_guard_scenario(self):
        manager = make_manager()

        token_a = manager.acquire(
            "resource-lock", "client-a", lease_duration=timedelta(milliseconds=50)
        )

        sleep(0.1)

        token_b = manager.acquire("resource-lock", "client-b")
        assert token_b > token_a

        assert manager.validate_fence_token("resource-lock", token_a) is False
        assert manager.validate_fence_token("resource-lock", token_b) is True

        class Resource:
            def __init__(self):
                self.value = 0
                self.last_token = 0

            def write(self, new_value: int, token: int, lock_manager: DistributedLockManager):
                if not lock_manager.validate_fence_token("resource-lock", token):
                    return False
                if token <= self.last_token:
                    return False
                self.value = new_value
                self.last_token = token
                return True

        resource = Resource()
        assert resource.write(100, token_a, manager) is False
        assert resource.write(200, token_b, manager) is True
        assert resource.value == 200
        assert resource.last_token == token_b
        assert resource.write(300, token_a, manager) is False
        assert resource.value == 200


class TestLockInfoAndQueries:
    def test_get_lock_info_nonexistent(self):
        manager = make_manager()
        assert manager.get_lock_info("nonexistent") is None

    def test_get_lock_info_held(self):
        manager = make_manager()
        token = manager.acquire("lock-1", "client-1")
        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.lock_name == "lock-1"
        assert info.state == LockState.HELD
        assert info.client_id == "client-1"
        assert info.fence_token == token
        assert info.reentrant_count == 1
        assert info.is_held is True

    def test_get_lock_info_no_side_effect_on_expired_lock(self):
        manager = make_manager()
        token = manager.acquire(
            "lock-1", "client-1", lease_duration=timedelta(milliseconds=50)
        )
        sleep(0.1)
        info1 = manager.get_lock_info("lock-1")
        assert info1 is not None
        assert info1.state == LockState.EXPIRED
        assert info1.client_id == "client-1"
        assert info1.fence_token == token
        info2 = manager.get_lock_info("lock-1")
        assert info2 is not None
        assert info2.client_id == "client-1"
        assert info2.fence_token == token
        assert info2.reentrant_count == 1

    def test_is_held_false_for_free(self):
        manager = make_manager()
        assert manager.is_held("lock-1") is False

    def test_is_held_by_false_for_other(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        assert manager.is_held_by("lock-1", "client-2") is False

    def test_count_locks(self):
        manager = make_manager()
        assert manager.count() == 0
        manager.acquire("lock-1", "client-1")
        assert manager.count() == 1
        manager.acquire("lock-2", "client-1")
        assert manager.count() == 2
        token = manager.acquire("lock-3", "client-1")
        manager.release("lock-3", "client-1", token)
        assert manager.count() == 2

    def test_force_release(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        assert manager.force_release("lock-1") is True
        assert manager.is_held("lock-1") is False

    def test_force_release_free_lock(self):
        manager = make_manager()
        assert manager.force_release("lock-1") is False

    def test_clear(self):
        manager = make_manager()
        manager.acquire("lock-1", "client-1")
        manager.acquire("lock-2", "client-2")
        assert manager.count() == 2
        manager.clear()
        assert manager.count() == 0


class TestManagerConfiguration:
    def test_default_lease_duration_applied(self):
        manager = make_manager(default_lease_duration=timedelta(seconds=90))
        manager.acquire("lock-1", "client-1")
        info = manager.get_lock_info("lock-1")
        assert info is not None
        assert info.lease_duration == timedelta(seconds=90)

    def test_negative_default_lease_duration_rejected(self):
        with pytest.raises(ValueError, match="default_lease_duration must be positive"):
            DistributedLockManager(default_lease_duration=timedelta(seconds=-1))

    def test_zero_default_lease_duration_rejected(self):
        with pytest.raises(ValueError, match="default_lease_duration must be positive"):
            DistributedLockManager(default_lease_duration=timedelta(seconds=0))
