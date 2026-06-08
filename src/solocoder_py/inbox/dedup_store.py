from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

from .clock import Clock, SystemClock
from .exceptions import DedupWindowConfigError
from .models import DedupResult, DedupStats, DedupWindowMode, InboxMessageRecord


@dataclass
class InboxDedupStore:
    max_count: Optional[int] = None
    max_time_seconds: Optional[float] = None
    ttl_seconds: float = 3600.0
    cleanup_interval_seconds: Optional[float] = None
    _clock: Clock = field(default_factory=SystemClock)
    _records: "OrderedDict[str, InboxMessageRecord]" = field(
        default_factory=OrderedDict
    )
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _total_received: int = 0
    _total_duplicates: int = 0
    _last_cleanup_at: float = field(
        default_factory=lambda: SystemClock().now()
    )

    def __post_init__(self) -> None:
        if self.max_count is None and self.max_time_seconds is None:
            raise DedupWindowConfigError(
                "At least one of max_count or max_time_seconds must be set"
            )
        if self.max_count is not None and self.max_count <= 0:
            raise DedupWindowConfigError("max_count must be positive")
        if self.max_time_seconds is not None and self.max_time_seconds <= 0:
            raise DedupWindowConfigError("max_time_seconds must be positive")
        if self.ttl_seconds <= 0:
            raise DedupWindowConfigError("ttl_seconds must be positive")
        if (
            self.cleanup_interval_seconds is not None
            and self.cleanup_interval_seconds <= 0
        ):
            raise DedupWindowConfigError("cleanup_interval_seconds must be positive")

    @property
    def window_mode(self) -> DedupWindowMode:
        if self.max_count is not None and self.max_time_seconds is not None:
            return DedupWindowMode.HYBRID
        elif self.max_count is not None:
            return DedupWindowMode.COUNT
        else:
            return DedupWindowMode.TIME

    def _evict_by_count(self) -> None:
        if self.max_count is None:
            return
        while len(self._records) > self.max_count:
            self._records.popitem(last=False)

    def _evict_by_time(self) -> None:
        if self.max_time_seconds is None:
            return
        now = self._clock.now()
        cutoff = now - self.max_time_seconds
        expired_ids = [
            msg_id
            for msg_id, record in self._records.items()
            if record.received_at <= cutoff
        ]
        for msg_id in expired_ids:
            del self._records[msg_id]

    def _evict_expired_by_ttl(self) -> int:
        expired_ids = [
            msg_id
            for msg_id, record in self._records.items()
            if record.is_expired(self.ttl_seconds, self._clock)
        ]
        for msg_id in expired_ids:
            del self._records[msg_id]
        return len(expired_ids)

    def _maybe_trigger_cleanup(self) -> None:
        if self.cleanup_interval_seconds is None:
            return
        now = self._clock.now()
        if now - self._last_cleanup_at >= self.cleanup_interval_seconds:
            self._evict_expired_by_ttl()
            self._last_cleanup_at = now

    def _slide_window(self) -> None:
        self._evict_by_time()
        self._evict_by_count()

    def _count_valid_records(self) -> int:
        count = 0
        now = self._clock.now()
        time_cutoff = (
            now - self.max_time_seconds if self.max_time_seconds is not None else None
        )
        count_limit = self.max_count

        records_items = list(self._records.items())
        if count_limit is not None and len(records_items) > count_limit:
            records_items = records_items[len(records_items) - count_limit:]

        for msg_id, record in records_items:
            if time_cutoff is not None and record.received_at <= time_cutoff:
                continue
            if record.is_expired(self.ttl_seconds, self._clock):
                continue
            count += 1

        return count

    def _valid_records_list(self) -> list[InboxMessageRecord]:
        result: list[InboxMessageRecord] = []
        now = self._clock.now()
        time_cutoff = (
            now - self.max_time_seconds if self.max_time_seconds is not None else None
        )
        count_limit = self.max_count

        records_items = list(self._records.items())
        if count_limit is not None and len(records_items) > count_limit:
            records_items = records_items[len(records_items) - count_limit:]

        for msg_id, record in records_items:
            if time_cutoff is not None and record.received_at <= time_cutoff:
                continue
            if record.is_expired(self.ttl_seconds, self._clock):
                continue
            result.append(record.snapshot())

        return result

    def check_duplicate(self, message_id: str) -> DedupResult:
        if not message_id:
            raise ValueError("message_id cannot be empty")

        with self._lock:
            self._maybe_trigger_cleanup()
            self._slide_window()

            record = self._records.get(message_id)
            if record is not None:
                if record.is_expired(self.ttl_seconds, self._clock):
                    del self._records[message_id]
                else:
                    self._total_received += 1
                    self._total_duplicates += 1
                    return DedupResult(
                        is_duplicate=True,
                        record=record.snapshot(),
                    )

            now = self._clock.now()
            new_record = InboxMessageRecord(
                message_id=message_id,
                received_at=now,
            )
            self._records[message_id] = new_record
            self._records.move_to_end(message_id)
            self._total_received += 1
            self._slide_window()

            return DedupResult(
                is_duplicate=False,
                record=new_record.snapshot(),
            )

    def _is_record_valid(
        self, message_id: str, record: InboxMessageRecord
    ) -> bool:
        now = self._clock.now()
        if self.max_time_seconds is not None:
            time_cutoff = now - self.max_time_seconds
            if record.received_at <= time_cutoff:
                return False
        if record.is_expired(self.ttl_seconds, self._clock):
            return False
        if self.max_count is not None:
            records_list = list(self._records.keys())
            if len(records_list) > self.max_count:
                start = len(records_list) - self.max_count
                if message_id not in records_list[start:]:
                    return False
        return True

    def contains(self, message_id: str) -> bool:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        with self._lock:
            record = self._records.get(message_id)
            if record is None:
                return False
            return self._is_record_valid(message_id, record)

    def get_record(self, message_id: str) -> Optional[InboxMessageRecord]:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        with self._lock:
            record = self._records.get(message_id)
            if record is None:
                return None
            if not self._is_record_valid(message_id, record):
                return None
            return record.snapshot()

    def window_count(self) -> int:
        with self._lock:
            return self._count_valid_records()

    def get_stats(self) -> DedupStats:
        with self._lock:
            window_size = self._count_valid_records()
            total_received = self._total_received
            total_duplicates = self._total_duplicates
            hit_rate = (
                (total_duplicates / total_received) if total_received > 0 else 0.0
            )
            return DedupStats(
                window_size=window_size,
                total_received=total_received,
                total_duplicates=total_duplicates,
                hit_rate=hit_rate,
            )

    def cleanup_expired(self) -> int:
        with self._lock:
            removed = self._evict_expired_by_ttl()
            self._last_cleanup_at = self._clock.now()
            return removed

    def remove(self, message_id: str) -> bool:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        with self._lock:
            if message_id in self._records:
                del self._records[message_id]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._total_received = 0
            self._total_duplicates = 0
            self._last_cleanup_at = self._clock.now()

    def list_records(self) -> list[InboxMessageRecord]:
        with self._lock:
            return self._valid_records_list()
