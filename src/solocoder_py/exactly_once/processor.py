from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .exceptions import (
    AtomicCommitInterruptedError,
    CheckpointNotFoundError,
    InvalidOffsetError,
)
from .models import (
    Checkpoint,
    DedupRecord,
    Message,
    ProcessResult,
    ProcessStatus,
    ReplayResult,
)
from .store import (
    CheckpointStore,
    Clock,
    DedupStore,
    InMemoryMessageSource,
    SystemClock,
)


@dataclass
class ExactlyOnceProcessor:
    message_source: InMemoryMessageSource
    dedup_store: DedupStore
    checkpoint_store: CheckpointStore
    _clock: Clock = field(default_factory=SystemClock)
    _current_offset: int = -1
    _auto_commit_interval: int = 1
    _uncommitted_records: List[DedupRecord] = field(default_factory=list)
    _uncommitted_results: Dict[str, Any] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _recovered: bool = False

    def __post_init__(self) -> None:
        if self._auto_commit_interval <= 0:
            raise ValueError("auto_commit_interval must be positive")

    @classmethod
    def create(
        cls,
        max_dedup_size: Optional[int] = None,
        auto_commit_interval: int = 1,
        clock: Optional[Clock] = None,
    ) -> "ExactlyOnceProcessor":
        effective_clock = clock if clock is not None else SystemClock()
        return cls(
            message_source=InMemoryMessageSource(_clock=effective_clock),
            dedup_store=DedupStore(
                max_size=max_dedup_size, _clock=effective_clock
            ),
            checkpoint_store=CheckpointStore(_clock=effective_clock),
            _clock=effective_clock,
            _auto_commit_interval=auto_commit_interval,
        )

    @property
    def current_offset(self) -> int:
        with self._lock:
            return self._current_offset

    @property
    def committed_offset(self) -> int:
        cp = self.checkpoint_store.get_latest_or_none()
        return cp.committed_offset if cp is not None else -1

    @property
    def is_recovered(self) -> bool:
        return self._recovered

    @property
    def auto_commit_interval(self) -> int:
        return self._auto_commit_interval

    @property
    def uncommitted_count(self) -> int:
        with self._lock:
            return len(self._uncommitted_records)

    def publish_message(self, message_id: str, payload: Any) -> int:
        return self.message_source.publish(message_id, payload)

    def publish_batch(
        self, messages: List[tuple[str, Any]]
    ) -> List[int]:
        return self.message_source.publish_batch(messages)

    def recover_from_checkpoint(self) -> Checkpoint:
        with self._lock:
            cp = self.checkpoint_store.restore_from_checkpoint(
                self.dedup_store
            )
            if cp is None:
                self._current_offset = -1
                self._uncommitted_records.clear()
                self._uncommitted_results.clear()
                raise CheckpointNotFoundError()

            self._current_offset = cp.committed_offset
            self._uncommitted_records.clear()
            self._uncommitted_results.clear()
            self._recovered = True
            return cp

    def recover_or_start_fresh(self) -> Optional[Checkpoint]:
        with self._lock:
            try:
                return self.recover_from_checkpoint()
            except CheckpointNotFoundError:
                self._current_offset = -1
                self._uncommitted_records.clear()
                self._uncommitted_results.clear()
                self._recovered = True
                return None

    def process_next(
        self, handler: Optional[Callable[[Message], Any]] = None
    ) -> Optional[ProcessResult]:
        with self._lock:
            next_offset = self._current_offset + 1
            if next_offset >= self.message_source.next_offset:
                return None

            msg = self.message_source.get_message(next_offset)

            prev_uncommitted_len = len(self._uncommitted_records)
            prev_offset = self._current_offset

            try:
                result = self._process_single(msg, handler, replaying=False)

                if (
                    result.is_new
                    and len(self._uncommitted_records) >= self._auto_commit_interval
                ):
                    self._auto_checkpoint()

                return result
            except Exception:
                while len(self._uncommitted_records) > prev_uncommitted_len:
                    rec = self._uncommitted_records.pop()
                    self._uncommitted_results.pop(rec.message_id, None)
                self._current_offset = prev_offset
                raise

    def process_batch(
        self,
        max_count: int,
        handler: Optional[Callable[[Message], Any]] = None,
    ) -> List[ProcessResult]:
        if max_count <= 0:
            raise ValueError("max_count must be positive")

        results: List[ProcessResult] = []
        with self._lock:
            for _ in range(max_count):
                result = self.process_next(handler)
                if result is None:
                    break
                results.append(result)
            if self._uncommitted_records:
                self._auto_checkpoint()
        return results

    def process_all(
        self, handler: Optional[Callable[[Message], Any]] = None
    ) -> List[ProcessResult]:
        results: List[ProcessResult] = []
        with self._lock:
            while True:
                result = self.process_next(handler)
                if result is None:
                    break
                results.append(result)
            if self._uncommitted_records:
                self._auto_checkpoint()
        return results

    def _find_uncommitted(self, message_id: str) -> Optional[DedupRecord]:
        for rec in self._uncommitted_records:
            if rec.message_id == message_id:
                return rec
        return None

    def _process_single(
        self,
        msg: Message,
        handler: Optional[Callable[[Message], Any]],
        replaying: bool,
    ) -> ProcessResult:
        existing = self.dedup_store.get(msg.message_id)
        if existing is not None:
            self._current_offset = msg.offset
            status = (
                ProcessStatus.SKIPPED_REPLAY
                if replaying
                else ProcessStatus.DUPLICATE
            )
            return ProcessResult(
                message=msg.snapshot(),
                status=status,
                dedup_record=existing.snapshot(),
                processed_new=False,
            )

        uncommitted = self._find_uncommitted(msg.message_id)
        if uncommitted is not None:
            self._current_offset = msg.offset
            status = (
                ProcessStatus.SKIPPED_REPLAY
                if replaying
                else ProcessStatus.DUPLICATE
            )
            return ProcessResult(
                message=msg.snapshot(),
                status=status,
                dedup_record=uncommitted.snapshot(),
                processed_new=False,
            )

        result_data: Any = None
        if handler is not None:
            result_data = handler(msg)

        dedup_record = DedupRecord(
            message_id=msg.message_id,
            offset=msg.offset,
            processed_at=self._clock.now(),
            result_data=result_data,
            replayed=replaying,
        )

        self._uncommitted_records.append(dedup_record)
        self._uncommitted_results[msg.message_id] = result_data
        self._current_offset = msg.offset

        return ProcessResult(
            message=msg.snapshot(),
            status=ProcessStatus.NEW,
            dedup_record=dedup_record.snapshot(),
            processed_new=True,
        )

    def _auto_checkpoint(self) -> Optional[Checkpoint]:
        if not self._uncommitted_records:
            return None

        target_offset = self._uncommitted_records[-1].offset
        batch_records = list(self._uncommitted_records)

        try:
            self.checkpoint_store.prepare_batch(
                target_offset=target_offset,
                dedup_records=batch_records,
            )
            checkpoint = self.checkpoint_store.commit_batch(
                self.dedup_store
            )
            self._uncommitted_records.clear()
            self._uncommitted_results.clear()
            return checkpoint
        except Exception:
            self.checkpoint_store.rollback_batch()
            raise

    def commit_checkpoint(self) -> Optional[Checkpoint]:
        with self._lock:
            return self._auto_checkpoint()

    def replay_range(
        self,
        start_offset: int,
        end_offset: int,
        handler: Optional[Callable[[Message], Any]] = None,
    ) -> ReplayResult:
        if start_offset < 0:
            raise InvalidOffsetError(
                start_offset, "start_offset must be non-negative"
            )
        if end_offset < start_offset:
            raise InvalidOffsetError(
                end_offset,
                "end_offset must be >= start_offset",
            )

        messages = self.message_source.get_range(start_offset, end_offset)

        processed_count = 0
        duplicate_count = 0
        skipped_count = 0
        new_dedup_records: List[DedupRecord] = []

        with self._lock:
            original_offset = self._current_offset
            original_uncommitted = list(self._uncommitted_records)
            original_results = dict(self._uncommitted_results)

            try:
                for msg in messages:
                    existing = self.dedup_store.get(msg.message_id)
                    if existing is not None:
                        duplicate_count += 1
                        continue

                    result_data: Any = None
                    if handler is not None:
                        result_data = handler(msg)

                    dedup_record = DedupRecord(
                        message_id=msg.message_id,
                        offset=msg.offset,
                        processed_at=self._clock.now(),
                        result_data=result_data,
                        replayed=True,
                    )

                    already_in_uncommitted = False
                    for r in new_dedup_records:
                        if r.message_id == msg.message_id:
                            already_in_uncommitted = True
                            skipped_count += 1
                            break
                    if already_in_uncommitted:
                        continue

                    new_dedup_records.append(dedup_record)
                    processed_count += 1

                if new_dedup_records:
                    target_offset = max(
                        r.offset for r in new_dedup_records
                    )
                    try:
                        self.checkpoint_store.prepare_batch(
                            target_offset=target_offset,
                            dedup_records=new_dedup_records,
                        )
                        self.checkpoint_store.commit_batch(self.dedup_store)
                    except Exception:
                        self.checkpoint_store.rollback_batch()
                        raise
            finally:
                self._current_offset = original_offset
                self._uncommitted_records = original_uncommitted
                self._uncommitted_results = original_results

        return ReplayResult(
            start_offset=start_offset,
            end_offset=end_offset,
            total_messages=len(messages),
            processed_count=processed_count,
            duplicate_count=duplicate_count,
            skipped_count=skipped_count,
            replayed_dedup_records=[
                r.snapshot() for r in new_dedup_records
            ],
        )

    def replay_from(
        self,
        start_offset: int,
        handler: Optional[Callable[[Message], Any]] = None,
    ) -> ReplayResult:
        latest = self.message_source.latest_offset
        if latest < 0:
            return ReplayResult(
                start_offset=start_offset,
                end_offset=start_offset,
                total_messages=0,
                processed_count=0,
                duplicate_count=0,
                skipped_count=0,
            )
        return self.replay_range(start_offset, latest, handler)

    def process_message_at(
        self,
        offset: int,
        handler: Optional[Callable[[Message], Any]] = None,
    ) -> ProcessResult:
        with self._lock:
            msg = self.message_source.get_message(offset)
            return self._process_single(msg, handler, replaying=False)

    def force_evict_dedup(self, count: int = 1) -> List[DedupRecord]:
        return self.dedup_store.evict_oldest(count)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_offset": self._current_offset,
                "committed_offset": self.committed_offset,
                "dedup_size": self.dedup_store.size(),
                "checkpoint_count": self.checkpoint_store.checkpoint_count(),
                "uncommitted_count": len(self._uncommitted_records),
                "is_recovered": self._recovered,
                "message_source_size": self.message_source.size(),
            }

    def reset(self) -> None:
        with self._lock:
            self.message_source.clear()
            self.dedup_store.clear()
            self.checkpoint_store.clear()
            self._current_offset = -1
            self._uncommitted_records.clear()
            self._uncommitted_results.clear()
            self._recovered = False
