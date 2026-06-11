from __future__ import annotations

from typing import Any, List, Optional

from .exceptions import (
    RWLockError,
    RWLockNotHeldError,
    RWLockNotAcquiredError,
    RWLockUpgradeError,
)
from .models import LockMode, RWLockState, Waiter, WaiterType
from .scheduler import Scheduler


class RWLock:
    def __init__(self, scheduler: Scheduler) -> None:
        self._state: RWLockState = RWLockState()
        self._scheduler: Scheduler = scheduler

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    @property
    def state(self) -> RWLockState:
        return self._state

    def acquire_read(self, thread_id: Optional[Any] = None) -> None:
        tid = thread_id if thread_id is not None else self._scheduler.current_thread_id()

        if self._state.is_write_locked and self._state.writer_thread_id == tid:
            raise RWLockUpgradeError(
                "Cannot acquire read lock while holding write lock in the same thread"
            )

        while True:
            if self._state.is_free:
                self._state.mode = LockMode.READ
                self._state.readers[tid] = self._state.readers.get(tid, 0) + 1
                return

            if self._state.is_read_locked and not self._state.has_waiting_writers:
                self._state.readers[tid] = self._state.readers.get(tid, 0) + 1
                return

            ticket = self._state.generate_ticket()
            waiter = Waiter(thread_id=tid, waiter_type=WaiterType.READER, ticket=ticket)
            self._state.waiting_readers.append(waiter)

            try:
                self._scheduler.park(tid)
            except Exception:
                self._remove_waiter_from_queue(self._state.waiting_readers, ticket)
                raise

    def acquire_write(self, thread_id: Optional[Any] = None) -> None:
        tid = thread_id if thread_id is not None else self._scheduler.current_thread_id()

        if self._state.is_write_locked and self._state.writer_thread_id == tid:
            self._state.write_lock_count += 1
            return

        if self._state.is_held_by(tid):
            raise RWLockUpgradeError(
                "Cannot acquire write lock while holding read lock in the same thread"
            )

        while True:
            if self._state.is_free:
                self._state.mode = LockMode.WRITE
                self._state.writer_thread_id = tid
                self._state.write_lock_count = 1
                return

            ticket = self._state.generate_ticket()
            waiter = Waiter(thread_id=tid, waiter_type=WaiterType.WRITER, ticket=ticket)
            self._state.waiting_writers.append(waiter)

            try:
                self._scheduler.park(tid)
            except Exception:
                self._remove_waiter_from_queue(self._state.waiting_writers, ticket)
                raise

    def release(self, thread_id: Optional[Any] = None) -> None:
        tid = thread_id if thread_id is not None else self._scheduler.current_thread_id()

        if not self._state.is_held_by(tid):
            raise RWLockNotHeldError(f"Thread {tid} does not hold the lock")

        if self._state.is_write_locked:
            self._state.write_lock_count -= 1
            if self._state.write_lock_count > 0:
                return
            self._state.mode = LockMode.FREE
            self._state.writer_thread_id = None
        else:
            self._state.readers[tid] -= 1
            if self._state.readers[tid] <= 0:
                del self._state.readers[tid]
            if len(self._state.readers) > 0:
                return
            self._state.mode = LockMode.FREE

        self._wake_waiters()

    def _wake_waiters(self) -> None:
        if self._state.has_waiting_writers:
            first_writer = self._state.waiting_writers.popleft()
            self._scheduler.unpark(first_writer.thread_id)
            return

        if self._state.has_waiting_readers:
            reader_thread_ids = [w.thread_id for w in self._state.waiting_readers]
            self._state.waiting_readers.clear()
            self._scheduler.unpark_all(reader_thread_ids)

    def _remove_waiter_from_queue(self, queue, ticket: int) -> None:
        for i, waiter in enumerate(queue):
            if waiter.ticket == ticket:
                del queue[i]
                return
