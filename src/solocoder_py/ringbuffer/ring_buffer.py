from __future__ import annotations

import threading
import time
from typing import Generic, List, Optional, Tuple, Sequence

from .models import T, WriteMode, InvalidCapacityError, TimeoutError


class RingBuffer(Generic[T]):
    def __init__(
        self,
        capacity: int,
        write_mode: WriteMode = WriteMode.NO_OVERWRITE,
    ) -> None:
        if capacity <= 0:
            raise InvalidCapacityError(
                f"Capacity must be a positive integer, got {capacity}"
            )

        self._capacity: int = capacity
        self._write_mode: WriteMode = write_mode
        self._buffer: List[Optional[T]] = [None] * capacity
        self._read_ptr: int = 0
        self._write_ptr: int = 0
        self._count: int = 0
        self._lock: threading.Lock = threading.Lock()
        self._not_empty: threading.Condition = threading.Condition(self._lock)
        self._not_full: threading.Condition = threading.Condition(self._lock)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def write_mode(self) -> WriteMode:
        return self._write_mode

    def available_to_read(self) -> int:
        with self._lock:
            return self._count

    def available_to_write(self) -> int:
        with self._lock:
            return self._capacity - self._count

    def _advance_read(self, n: int = 1) -> None:
        self._read_ptr = (self._read_ptr + n) % self._capacity

    def _advance_write(self, n: int = 1) -> None:
        self._write_ptr = (self._write_ptr + n) % self._capacity

    def write(
        self,
        item: T,
        *,
        blocking: bool = False,
        timeout: Optional[float] = None,
        raise_timeout: bool = False,
    ) -> int:
        return self.write_batch(
            [item],
            blocking=blocking,
            timeout=timeout,
            raise_timeout=raise_timeout,
        )

    def write_batch(
        self,
        items: Sequence[T],
        *,
        blocking: bool = False,
        timeout: Optional[float] = None,
        raise_timeout: bool = False,
    ) -> int:
        if not items:
            return 0

        with self._lock:
            if self._write_mode == WriteMode.NO_OVERWRITE:
                if not blocking:
                    available = self._capacity - self._count
                    n_write = min(len(items), available)
                    if n_write == 0:
                        return 0
                    self._write_items(items[:n_write])
                    return n_write
                else:
                    return self._blocking_write_batch(items, timeout, raise_timeout)
            else:
                n_items = len(items)
                n_write = min(n_items, self._capacity)
                items_to_write = items[-n_write:]

                available = self._capacity - self._count
                overflow = max(0, n_items - available)

                if overflow > 0:
                    actual_overflow = min(overflow, self._count)
                    self._advance_read(actual_overflow)
                    self._count -= actual_overflow

                self._write_items(items_to_write)
                return n_write

    def _blocking_write_batch(
        self,
        items: Sequence[T],
        timeout: Optional[float],
        raise_timeout: bool,
    ) -> int:
        deadline = time.monotonic() + timeout if timeout is not None else None
        total_written = 0
        items_remaining = list(items)

        while items_remaining:
            available = self._capacity - self._count
            if available == 0:
                remaining = None
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        if raise_timeout and total_written == 0:
                            raise TimeoutError(
                                f"Write timed out after {timeout} seconds"
                            )
                        return total_written
                if not self._not_full.wait(timeout=remaining):
                    if raise_timeout and total_written == 0:
                        raise TimeoutError(
                            f"Write timed out after {timeout} seconds"
                        )
                    return total_written
                continue

            n_write = min(len(items_remaining), available)
            self._write_items(items_remaining[:n_write])
            total_written += n_write
            items_remaining = items_remaining[n_write:]

        return total_written

    def _write_items(self, items: Sequence[T]) -> None:
        n = len(items)
        first_segment = min(n, self._capacity - self._write_ptr)
        second_segment = n - first_segment

        for i in range(first_segment):
            self._buffer[self._write_ptr + i] = items[i]

        for i in range(second_segment):
            self._buffer[i] = items[first_segment + i]

        self._advance_write(n)
        self._count += n
        self._not_empty.notify_all()

    def read(
        self,
        *,
        blocking: bool = False,
        timeout: Optional[float] = None,
        raise_timeout: bool = False,
    ) -> Optional[T]:
        result = self.read_batch(
            1,
            blocking=blocking,
            timeout=timeout,
            raise_timeout=raise_timeout,
        )
        if not result:
            return None
        return result[0]

    def read_batch(
        self,
        max_count: int,
        *,
        blocking: bool = False,
        timeout: Optional[float] = None,
        raise_timeout: bool = False,
    ) -> List[T]:
        if max_count <= 0:
            return []

        with self._lock:
            if not blocking:
                available = self._count
                n_read = min(max_count, available)
                if n_read == 0:
                    return []
                return self._read_items(n_read)
            else:
                return self._blocking_read_batch(max_count, timeout, raise_timeout)

    def _blocking_read_batch(
        self,
        max_count: int,
        timeout: Optional[float],
        raise_timeout: bool,
    ) -> List[T]:
        deadline = time.monotonic() + timeout if timeout is not None else None

        while self._count == 0:
            remaining = None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if raise_timeout:
                        raise TimeoutError(
                            f"Read timed out after {timeout} seconds"
                        )
                    return []
            if not self._not_empty.wait(timeout=remaining):
                if raise_timeout:
                    raise TimeoutError(
                        f"Read timed out after {timeout} seconds"
                    )
                return []

        n_read = min(max_count, self._count)
        return self._read_items(n_read)

    def _read_items(self, n: int) -> List[T]:
        result: List[T] = []
        first_segment = min(n, self._capacity - self._read_ptr)
        second_segment = n - first_segment

        for i in range(first_segment):
            item = self._buffer[self._read_ptr + i]
            assert item is not None
            result.append(item)
            self._buffer[self._read_ptr + i] = None

        for i in range(second_segment):
            item = self._buffer[i]
            assert item is not None
            result.append(item)
            self._buffer[i] = None

        self._advance_read(n)
        self._count -= n
        self._not_full.notify_all()
        return result

    def clear(self) -> None:
        with self._lock:
            for i in range(self._capacity):
                self._buffer[i] = None
            self._read_ptr = 0
            self._write_ptr = 0
            self._count = 0
            self._not_full.notify_all()
