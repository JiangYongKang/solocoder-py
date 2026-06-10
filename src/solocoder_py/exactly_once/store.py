from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .exceptions import (
    CheckpointNotFoundError,
    DedupStoreOverflowError,
    InvalidOffsetError,
    MessageNotFoundError,
)
from .models import (
    Checkpoint,
    CommitBatch,
    DedupRecord,
    Message,
)


class Clock(ABC):
    @abstractmethod
    def now(self) -> float:
        ...

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot sleep for negative seconds")
        self._do_sleep(seconds)

    @abstractmethod
    def _do_sleep(self, seconds: float) -> None:
        ...


class SystemClock(Clock):
    def now(self) -> float:
        return time.monotonic()

    def _do_sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class ManualClock(Clock):
    def __init__(self, start_time: float = 0.0) -> None:
        self._current_time: float = start_time
        self._sleep_history: list[float] = []

    def now(self) -> float:
        return self._current_time

    def _do_sleep(self, seconds: float) -> None:
        self._sleep_history.append(seconds)
        self._current_time += seconds

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Cannot advance by negative seconds")
        self._current_time += seconds

    def set(self, time_value: float) -> None:
        self._current_time = time_value

    @property
    def sleep_history(self) -> list[float]:
        return list(self._sleep_history)


@dataclass
class InMemoryMessageSource:
    _messages: Dict[int, Message] = field(default_factory=dict)
    _next_offset: int = 0
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _clock: Clock = field(default_factory=SystemClock)

    def publish(self, message_id: str, payload: Any) -> int:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        with self._lock:
            offset = self._next_offset
            msg = Message(
                offset=offset,
                message_id=message_id,
                payload=payload,
                created_at=self._clock.now(),
            )
            self._messages[offset] = msg
            self._next_offset += 1
            return offset

    def publish_batch(self, messages: List[Tuple[str, Any]]) -> List[int]:
        offsets: List[int] = []
        for msg_id, payload in messages:
            offsets.append(self.publish(msg_id, payload))
        return offsets

    def get_message(self, offset: int) -> Message:
        if offset < 0:
            raise InvalidOffsetError(offset, "offset must be non-negative")
        with self._lock:
            if offset not in self._messages:
                raise MessageNotFoundError(offset)
            return self._messages[offset].snapshot()

    def get_range(
        self, start_offset: int, end_offset: Optional[int] = None
    ) -> List[Message]:
        if start_offset < 0:
            raise InvalidOffsetError(start_offset, "start_offset must be non-negative")
        with self._lock:
            effective_end = (
                end_offset if end_offset is not None else self._next_offset - 1
            )
            if effective_end < start_offset:
                return []
            results: List[Message] = []
            for off in range(start_offset, effective_end + 1):
                if off in self._messages:
                    results.append(self._messages[off].snapshot())
            return results

    def iter_from(self, start_offset: int) -> Iterator[Message]:
        if start_offset < 0:
            raise InvalidOffsetError(start_offset, "start_offset must be non-negative")
        offset = start_offset
        while True:
            with self._lock:
                if offset >= self._next_offset:
                    break
                if offset in self._messages:
                    yield self._messages[offset].snapshot()
            offset += 1

    @property
    def latest_offset(self) -> int:
        with self._lock:
            if self._next_offset == 0:
                return -1
            return self._next_offset - 1

    @property
    def next_offset(self) -> int:
        with self._lock:
            return self._next_offset

    def size(self) -> int:
        with self._lock:
            return len(self._messages)

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()
            self._next_offset = 0

    def contains_offset(self, offset: int) -> bool:
        with self._lock:
            return offset in self._messages


@dataclass
class DedupStore:
    max_size: Optional[int] = None
    _records: "OrderedDict[str, DedupRecord]" = field(
        default_factory=OrderedDict
    )
    _offset_to_id: Dict[int, str] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _clock: Clock = field(default_factory=SystemClock)

    def __post_init__(self) -> None:
        if self.max_size is not None and self.max_size <= 0:
            raise ValueError("max_size must be positive or None")

    def contains(self, message_id: str) -> bool:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        with self._lock:
            return message_id in self._records

    def contains_offset(self, offset: int) -> bool:
        if offset < 0:
            raise InvalidOffsetError(offset, "offset must be non-negative")
        with self._lock:
            return offset in self._offset_to_id

    def get(self, message_id: str) -> Optional[DedupRecord]:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        with self._lock:
            record = self._records.get(message_id)
            return record.snapshot() if record is not None else None

    def get_by_offset(self, offset: int) -> Optional[DedupRecord]:
        if offset < 0:
            raise InvalidOffsetError(offset, "offset must be non-negative")
        with self._lock:
            msg_id = self._offset_to_id.get(offset)
            if msg_id is None:
                return None
            record = self._records.get(msg_id)
            return record.snapshot() if record is not None else None

    def put(
        self,
        message_id: str,
        offset: int,
        result_data: Optional[Any] = None,
        replayed: bool = False,
    ) -> DedupRecord:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        if offset < 0:
            raise InvalidOffsetError(offset, "offset must be non-negative")

        with self._lock:
            if message_id in self._records:
                existing = self._records[message_id]
                existing.result_data = result_data
                existing.replayed = existing.replayed or replayed
                self._records.move_to_end(message_id)
                return existing.snapshot()

            if (
                self.max_size is not None
                and len(self._records) >= self.max_size
            ):
                raise DedupStoreOverflowError(self.max_size)

            record = DedupRecord(
                message_id=message_id,
                offset=offset,
                processed_at=self._clock.now(),
                result_data=result_data,
                replayed=replayed,
            )
            self._records[message_id] = record
            self._offset_to_id[offset] = message_id
            return record.snapshot()

    def put_batch(self, records: List[DedupRecord]) -> None:
        with self._lock:
            for r in records:
                if r.message_id in self._records:
                    self._records.move_to_end(r.message_id)
                    continue
                if (
                    self.max_size is not None
                    and len(self._records) >= self.max_size
                ):
                    raise DedupStoreOverflowError(self.max_size)
                self._records[r.message_id] = DedupRecord(
                    message_id=r.message_id,
                    offset=r.offset,
                    processed_at=r.processed_at,
                    result_data=r.result_data,
                    replayed=r.replayed,
                )
                self._offset_to_id[r.offset] = r.message_id

    def remove(self, message_id: str) -> bool:
        if not message_id:
            raise ValueError("message_id cannot be empty")
        with self._lock:
            record = self._records.pop(message_id, None)
            if record is not None:
                self._offset_to_id.pop(record.offset, None)
                return True
            return False

    def evict_oldest(self, count: int = 1) -> List[DedupRecord]:
        if count <= 0:
            raise ValueError("count must be positive")
        with self._lock:
            evicted: List[DedupRecord] = []
            for _ in range(min(count, len(self._records))):
                _, record = self._records.popitem(last=False)
                self._offset_to_id.pop(record.offset, None)
                evicted.append(record.snapshot())
            return evicted

    def size(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._offset_to_id.clear()

    def list_records(self) -> List[DedupRecord]:
        with self._lock:
            return [r.snapshot() for r in self._records.values()]

    def list_message_ids(self) -> List[str]:
        with self._lock:
            return list(self._records.keys())


@dataclass
class CheckpointStore:
    _checkpoints: List[Checkpoint] = field(default_factory=list)
    _pending_batch: Optional[CommitBatch] = None
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _clock: Clock = field(default_factory=SystemClock)
    _simulate_crash_after_prepare: bool = False
    _simulate_crash_after_dedup: bool = False

    @property
    def has_pending_batch(self) -> bool:
        with self._lock:
            return self._pending_batch is not None

    @property
    def pending_batch(self) -> Optional[CommitBatch]:
        with self._lock:
            return self._pending_batch

    def prepare_batch(
        self,
        target_offset: int,
        dedup_records: List[DedupRecord],
    ) -> CommitBatch:
        with self._lock:
            if self._pending_batch is not None:
                raise RuntimeError(
                    "Cannot prepare batch: another batch is pending commit"
                )
            batch = CommitBatch(
                target_offset=target_offset,
                message_ids=[r.message_id for r in dedup_records],
                dedup_records=[r.snapshot() for r in dedup_records],
                batch_id=str(uuid.uuid4()),
                started_at=self._clock.now(),
                is_prepared=True,
            )
            self._pending_batch = batch
            return batch

    def simulate_crash_after_prepare(self, enable: bool = True) -> None:
        self._simulate_crash_after_prepare = enable

    def simulate_crash_after_dedup(self, enable: bool = True) -> None:
        self._simulate_crash_after_dedup = enable

    def commit_batch(
        self,
        dedup_store: DedupStore,
    ) -> Checkpoint:
        with self._lock:
            batch = self._pending_batch
            if batch is None or not batch.is_prepared:
                raise RuntimeError("No prepared batch to commit")

            if self._simulate_crash_after_prepare:
                self._simulate_crash_after_prepare = False
                from .exceptions import AtomicCommitInterruptedError

                raise AtomicCommitInterruptedError(
                    message_ids=batch.message_ids,
                    offset=batch.target_offset,
                )

            dedup_store.put_batch(batch.dedup_records)

            if self._simulate_crash_after_dedup:
                self._simulate_crash_after_dedup = False
                from .exceptions import AtomicCommitInterruptedError

                raise AtomicCommitInterruptedError(
                    message_ids=batch.message_ids,
                    offset=batch.target_offset,
                )

            last_msg_id = (
                batch.message_ids[-1] if batch.message_ids else None
            )
            checkpoint = Checkpoint(
                committed_offset=batch.target_offset,
                checkpoint_id=str(uuid.uuid4()),
                created_at=self._clock.now(),
                dedup_count=dedup_store.size(),
                last_message_id=last_msg_id,
            )
            self._checkpoints.append(checkpoint)
            self._pending_batch = None
            batch.is_committed = True
            return checkpoint.snapshot()

    def rollback_batch(self) -> Optional[CommitBatch]:
        with self._lock:
            batch = self._pending_batch
            self._pending_batch = None
            return batch

    def get_latest(self) -> Checkpoint:
        with self._lock:
            if not self._checkpoints:
                raise CheckpointNotFoundError()
            return self._checkpoints[-1].snapshot()

    def get_latest_or_none(self) -> Optional[Checkpoint]:
        with self._lock:
            if not self._checkpoints:
                return None
            return self._checkpoints[-1].snapshot()

    def get_all(self) -> List[Checkpoint]:
        with self._lock:
            return [c.snapshot() for c in self._checkpoints]

    def restore_from_checkpoint(
        self,
        dedup_store: DedupStore,
        checkpoint: Optional[Checkpoint] = None,
    ) -> Optional[Checkpoint]:
        with self._lock:
            target_cp = checkpoint
            if target_cp is None:
                if not self._checkpoints:
                    return None
                target_cp = self._checkpoints[-1]

            batch = self._pending_batch
            if (
                batch is not None
                and batch.is_prepared
                and not batch.is_committed
            ):
                self._pending_batch = None

            restored = target_cp.snapshot()
            return restored

    def checkpoint_count(self) -> int:
        with self._lock:
            return len(self._checkpoints)

    def clear(self) -> None:
        with self._lock:
            self._checkpoints.clear()
            self._pending_batch = None
