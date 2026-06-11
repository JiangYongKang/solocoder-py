import pytest

from solocoder_py.rwlock import (
    LockMode,
    ManualScheduler,
    Parked,
    RWLock,
    RWLockError,
    RWLockNotHeldError,
    RWLockUpgradeError,
    WaiterType,
)
from .conftest import make_lock, make_scheduler


def acquire_with_park(lock: RWLock, scheduler: ManualScheduler, mode: str, thread_id: str) -> None:
    scheduler.set_current_thread(thread_id)
    try:
        if mode == "read":
            lock.acquire_read()
        else:
            lock.acquire_write()
    except Parked:
        pass


class TestRWLockStateModel:
    def test_initial_state(self):
        from solocoder_py.rwlock import RWLockState

        state = RWLockState()
        assert state.mode == LockMode.FREE
        assert state.writer_thread_id is None
        assert state.reader_count == 0
        assert state.has_waiting_writers is False
        assert state.has_waiting_readers is False
        assert state.is_free is True
        assert state.is_read_locked is False
        assert state.is_write_locked is False

    def test_generate_ticket_monotonic(self):
        from solocoder_py.rwlock import RWLockState

        state = RWLockState()
        t1 = state.generate_ticket()
        t2 = state.generate_ticket()
        t3 = state.generate_ticket()
        assert t1 == 0
        assert t2 == 1
        assert t3 == 2

    def test_waiter_negative_ticket_rejected(self):
        from solocoder_py.rwlock import Waiter, WaiterType

        with pytest.raises(ValueError, match="ticket cannot be negative"):
            Waiter(thread_id="t1", waiter_type=WaiterType.READER, ticket=-1)


class TestManualScheduler:
    def test_set_and_get_current_thread(self):
        scheduler = make_scheduler()
        scheduler.set_current_thread("thread-1")
        assert scheduler.current_thread_id() == "thread-1"

    def test_get_current_thread_without_set_raises(self):
        scheduler = make_scheduler()
        with pytest.raises(RuntimeError, match="current_thread_id is not set"):
            scheduler.current_thread_id()

    def test_park_raises_parked_exception(self):
        scheduler = make_scheduler()
        with pytest.raises(Parked):
            scheduler.park("thread-1")
        assert scheduler.is_parked("thread-1") is True
        assert scheduler.parked_count == 1

    def test_unpark(self):
        scheduler = make_scheduler()
        with pytest.raises(Parked):
            scheduler.park("thread-1")

        result = scheduler.unpark("thread-1")
        assert result is True
        assert scheduler.is_parked("thread-1") is False
        assert scheduler.parked_count == 0

    def test_unpark_not_parked_returns_false(self):
        scheduler = make_scheduler()
        result = scheduler.unpark("nonexistent")
        assert result is False

    def test_park_already_parked_raises(self):
        scheduler = make_scheduler()
        with pytest.raises(Parked):
            scheduler.park("thread-1")
        with pytest.raises(ValueError, match="already parked"):
            scheduler.park("thread-1")

    def test_unpark_all(self):
        scheduler = make_scheduler()
        with pytest.raises(Parked):
            scheduler.park("t1")
        with pytest.raises(Parked):
            scheduler.park("t2")
        with pytest.raises(Parked):
            scheduler.park("t3")
        assert scheduler.parked_count == 3

        count = scheduler.unpark_all(["t1", "t3", "nonexistent"])
        assert count == 2
        assert scheduler.parked_count == 1
        assert scheduler.is_parked("t2") is True


class TestReadLockSharing:
    def test_single_reader_acquire_and_release(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()
        assert lock.state.is_read_locked is True
        assert lock.state.reader_count == 1

        lock.release()
        assert lock.state.is_free is True
        assert lock.state.reader_count == 0

    def test_multiple_readers_share_lock(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()

        scheduler.set_current_thread("reader-2")
        lock.acquire_read()

        scheduler.set_current_thread("reader-3")
        lock.acquire_read()

        assert lock.state.is_read_locked is True
        assert lock.state.reader_count == 3

        scheduler.set_current_thread("reader-2")
        lock.release()
        assert lock.state.reader_count == 2
        assert lock.state.is_read_locked is True

        scheduler.set_current_thread("reader-1")
        lock.release()
        assert lock.state.reader_count == 1

        scheduler.set_current_thread("reader-3")
        lock.release()
        assert lock.state.is_free is True

    def test_same_reader_reentrant_acquire(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()
        lock.acquire_read()
        lock.acquire_read()

        assert lock.state.reader_count == 3
        assert lock.state.readers["reader-1"] == 3

        lock.release()
        assert lock.state.reader_count == 2

        lock.release()
        assert lock.state.reader_count == 1

        lock.release()
        assert lock.state.is_free is True


class TestWriteLockExclusive:
    def test_single_writer_acquire_and_release(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()
        assert lock.state.is_write_locked is True
        assert lock.state.writer_thread_id == "writer-1"

        lock.release()
        assert lock.state.is_free is True

    def test_same_writer_reentrant_acquire(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()
        lock.acquire_write()
        lock.acquire_write()

        assert lock.state.write_lock_count == 3

        lock.release()
        assert lock.state.write_lock_count == 2
        assert lock.state.is_write_locked is True

        lock.release()
        assert lock.state.write_lock_count == 1

        lock.release()
        assert lock.state.is_free is True

    def test_second_writer_blocked_by_writer(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()

        acquire_with_park(lock, scheduler, "write", "writer-2")

        assert scheduler.is_parked("writer-2") is True
        assert lock.state.has_waiting_writers is True

        scheduler.set_current_thread("writer-1")
        lock.release()

        assert scheduler.is_parked("writer-2") is False
        assert lock.state.is_write_locked is True
        assert lock.state.writer_thread_id == "writer-2"

    def test_reader_blocked_by_writer(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()

        acquire_with_park(lock, scheduler, "read", "reader-1")

        assert scheduler.is_parked("reader-1") is True
        assert lock.state.has_waiting_readers is True


class TestReadThenWrite:
    def test_writer_waits_for_all_readers(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()

        scheduler.set_current_thread("reader-2")
        lock.acquire_read()

        acquire_with_park(lock, scheduler, "write", "writer-1")
        assert scheduler.is_parked("writer-1") is True
        assert lock.state.has_waiting_writers is True

        scheduler.set_current_thread("reader-1")
        lock.release()
        assert scheduler.is_parked("writer-1") is True
        assert lock.state.reader_count == 1

        scheduler.set_current_thread("reader-2")
        lock.release()
        assert scheduler.is_parked("writer-1") is False
        assert lock.state.is_write_locked is True
        assert lock.state.writer_thread_id == "writer-1"


class TestWriterPriority:
    def test_new_reader_blocked_when_writer_waiting(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()

        acquire_with_park(lock, scheduler, "write", "writer-1")
        assert scheduler.is_parked("writer-1") is True

        acquire_with_park(lock, scheduler, "read", "reader-2")
        assert scheduler.is_parked("reader-2") is True
        assert lock.state.has_waiting_readers is True

        scheduler.set_current_thread("reader-1")
        lock.release()

        assert scheduler.is_parked("writer-1") is False
        assert lock.state.is_write_locked is True
        assert lock.state.writer_thread_id == "writer-1"

        assert scheduler.is_parked("reader-2") is True

    def test_writer_released_all_waiting_readers_wake(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()

        acquire_with_park(lock, scheduler, "read", "reader-1")
        acquire_with_park(lock, scheduler, "read", "reader-2")
        acquire_with_park(lock, scheduler, "read", "reader-3")

        assert scheduler.parked_count == 3

        scheduler.set_current_thread("writer-1")
        lock.release()

        assert scheduler.is_parked("reader-1") is False
        assert scheduler.is_parked("reader-2") is False
        assert scheduler.is_parked("reader-3") is False
        assert lock.state.is_read_locked is True
        assert lock.state.reader_count == 3


class TestBoundaryConditions:
    def test_writer_acquires_when_zero_readers(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        assert lock.state.is_free is True

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()

        assert lock.state.is_write_locked is True
        assert lock.state.writer_thread_id == "writer-1"
        assert scheduler.parked_count == 0

    def test_explicit_thread_id_parameter(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        lock.acquire_read(thread_id="my-reader")
        assert lock.state.reader_count == 1
        assert "my-reader" in lock.state.readers

        lock.release(thread_id="my-reader")
        assert lock.state.is_free is True


class TestErrorCases:
    def test_release_lock_not_held(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        with pytest.raises(RWLockNotHeldError):
            lock.release()

    def test_double_release(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()
        lock.release()

        with pytest.raises(RWLockNotHeldError):
            lock.release()

    def test_release_wrong_thread(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()

        scheduler.set_current_thread("reader-2")
        with pytest.raises(RWLockNotHeldError):
            lock.release()

    def test_write_lock_holder_cannot_acquire_read(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()

        with pytest.raises(RWLockUpgradeError):
            lock.acquire_read()

    def test_read_lock_holder_cannot_acquire_write(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()

        with pytest.raises(RWLockUpgradeError):
            lock.acquire_write()

    def test_lock_requires_scheduler(self):
        with pytest.raises(ValueError, match="scheduler must be provided"):
            RWLock()


class TestFairnessAndComplexScenarios:
    def test_multiple_writers_fifo_order(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()

        acquire_with_park(lock, scheduler, "write", "writer-2")
        acquire_with_park(lock, scheduler, "write", "writer-3")

        assert scheduler.parked_count == 2

        scheduler.set_current_thread("writer-1")
        lock.release()
        assert lock.state.writer_thread_id == "writer-2"
        assert scheduler.is_parked("writer-3") is True

        scheduler.set_current_thread("writer-2")
        lock.release()
        assert lock.state.writer_thread_id == "writer-3"
        assert scheduler.is_parked("writer-3") is False

    def test_reader_then_writer_then_reader_fairness(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("reader-1")
        lock.acquire_read()

        acquire_with_park(lock, scheduler, "write", "writer-1")
        acquire_with_park(lock, scheduler, "read", "reader-2")
        acquire_with_park(lock, scheduler, "read", "reader-3")

        assert scheduler.parked_count == 3

        scheduler.set_current_thread("reader-1")
        lock.release()

        assert lock.state.is_write_locked is True
        assert lock.state.writer_thread_id == "writer-1"
        assert scheduler.is_parked("reader-2") is True
        assert scheduler.is_parked("reader-3") is True

        scheduler.set_current_thread("writer-1")
        lock.release()

        assert lock.state.is_read_locked is True
        assert lock.state.reader_count == 2
        assert scheduler.parked_count == 0

    def test_writer_reentrant_with_waiter(self):
        scheduler = make_scheduler()
        lock = make_lock(scheduler)

        scheduler.set_current_thread("writer-1")
        lock.acquire_write()
        lock.acquire_write()

        acquire_with_park(lock, scheduler, "write", "writer-2")
        assert scheduler.is_parked("writer-2") is True

        scheduler.set_current_thread("writer-1")
        lock.release()
        assert lock.state.write_lock_count == 1
        assert lock.state.is_write_locked is True
        assert scheduler.is_parked("writer-2") is True

        lock.release()
        assert lock.state.writer_thread_id == "writer-2"
        assert scheduler.is_parked("writer-2") is False
