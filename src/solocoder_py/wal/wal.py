from __future__ import annotations

import threading
from typing import Dict, Iterator, List, Optional

from .exceptions import (
    EmptyWalError,
    InvalidTruncateLsnError,
    LsnNotFoundError,
    TruncatedLsnError,
)
from .models import LogEntry


class WriteAheadLog:
    def __init__(self) -> None:
        self._entries: Dict[int, LogEntry] = {}
        self._next_lsn: int = 0
        self._min_readable_lsn: int = 0
        self._lock: threading.RLock = threading.RLock()

    @property
    def min_readable_lsn(self) -> int:
        with self._lock:
            return self._min_readable_lsn

    @property
    def max_lsn(self) -> int:
        with self._lock:
            if self._next_lsn == 0:
                return -1
            return self._next_lsn - 1

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return self._next_lsn == 0 or self._min_readable_lsn > self.max_lsn

    def append(self, data: object) -> int:
        with self._lock:
            lsn = self._next_lsn
            entry = LogEntry(lsn=lsn, data=data)
            self._entries[lsn] = entry
            self._next_lsn += 1
            return lsn

    def read(self, lsn: int) -> LogEntry:
        with self._lock:
            if self.is_empty:
                raise EmptyWalError("Write-ahead log is empty")
            if lsn < self._min_readable_lsn:
                raise TruncatedLsnError(lsn, self._min_readable_lsn)
            if lsn > self.max_lsn:
                raise LsnNotFoundError(lsn, self._min_readable_lsn, self.max_lsn)
            return self._entries[lsn]

    def read_range(
        self, start_lsn: int, end_lsn: Optional[int] = None
    ) -> List[LogEntry]:
        with self._lock:
            if self.is_empty:
                return []

            effective_end = end_lsn if end_lsn is not None else self.max_lsn

            if start_lsn < self._min_readable_lsn:
                raise TruncatedLsnError(start_lsn, self._min_readable_lsn)
            if effective_end > self.max_lsn:
                raise LsnNotFoundError(
                    effective_end, self._min_readable_lsn, self.max_lsn
                )
            if start_lsn > effective_end:
                return []

            return [self._entries[lsn] for lsn in range(start_lsn, effective_end + 1)]

    def replay(self, from_lsn: Optional[int] = None) -> Iterator[LogEntry]:
        with self._lock:
            if self.is_empty:
                return iter([])

            start = from_lsn if from_lsn is not None else self._min_readable_lsn

            if start < self._min_readable_lsn:
                raise TruncatedLsnError(start, self._min_readable_lsn)
            if start > self.max_lsn:
                return iter([])

            entries: List[LogEntry] = []
            for lsn in range(start, self._next_lsn):
                if lsn not in self._entries:
                    break
                entries.append(self._entries[lsn])

            return iter(entries)

    def truncate(self, lsn: int) -> None:
        with self._lock:
            if self.is_empty:
                raise EmptyWalError("Write-ahead log is empty, cannot truncate")

            if lsn < self._min_readable_lsn:
                raise InvalidTruncateLsnError(
                    lsn, self._min_readable_lsn, self.max_lsn
                )
            if lsn > self.max_lsn:
                raise InvalidTruncateLsnError(
                    lsn, self._min_readable_lsn, self.max_lsn
                )

            for removed_lsn in range(self._min_readable_lsn, lsn + 1):
                if removed_lsn in self._entries:
                    del self._entries[removed_lsn]

            self._min_readable_lsn = lsn + 1

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._next_lsn = 0
            self._min_readable_lsn = 0
