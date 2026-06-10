from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .exceptions import InvalidOffsetError


class ProcessStatus(str, Enum):
    NEW = "new"
    DUPLICATE = "duplicate"
    SKIPPED_REPLAY = "skipped_replay"


@dataclass
class Message:
    offset: int
    message_id: str
    payload: Any
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise InvalidOffsetError(self.offset, "offset must be non-negative")
        if not self.message_id:
            raise ValueError("message_id cannot be empty")

    def snapshot(self) -> "Message":
        return Message(
            offset=self.offset,
            message_id=self.message_id,
            payload=copy.deepcopy(self.payload),
            created_at=self.created_at,
        )


@dataclass
class DedupRecord:
    message_id: str
    offset: int
    processed_at: float
    result_data: Optional[Any] = None
    replayed: bool = False

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id cannot be empty")
        if self.offset < 0:
            raise InvalidOffsetError(self.offset, "offset must be non-negative")

    def snapshot(self) -> "DedupRecord":
        return DedupRecord(
            message_id=self.message_id,
            offset=self.offset,
            processed_at=self.processed_at,
            result_data=self.result_data,
            replayed=self.replayed,
        )


@dataclass
class Checkpoint:
    committed_offset: int
    checkpoint_id: str
    created_at: float
    dedup_count: int = 0
    last_message_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.committed_offset < -1:
            raise InvalidOffsetError(
                self.committed_offset,
                "committed_offset must be >= -1 (-1 means nothing committed yet)",
            )
        if not self.checkpoint_id:
            raise ValueError("checkpoint_id cannot be empty")

    def snapshot(self) -> "Checkpoint":
        return Checkpoint(
            committed_offset=self.committed_offset,
            checkpoint_id=self.checkpoint_id,
            created_at=self.created_at,
            dedup_count=self.dedup_count,
            last_message_id=self.last_message_id,
        )


@dataclass
class ProcessResult:
    message: Message
    status: ProcessStatus
    dedup_record: Optional[DedupRecord] = None
    processed_new: bool = False

    @property
    def is_duplicate(self) -> bool:
        return self.status == ProcessStatus.DUPLICATE

    @property
    def is_new(self) -> bool:
        return self.status == ProcessStatus.NEW

    @property
    def is_skipped_replay(self) -> bool:
        return self.status == ProcessStatus.SKIPPED_REPLAY

    @property
    def should_process(self) -> bool:
        return self.status == ProcessStatus.NEW

    @property
    def previous_result(self) -> Optional[Any]:
        if self.dedup_record is not None:
            return self.dedup_record.result_data
        return None


@dataclass
class CommitBatch:
    target_offset: int
    message_ids: list[str]
    dedup_records: list[DedupRecord]
    batch_id: str
    started_at: float
    is_prepared: bool = False
    is_committed: bool = False

    def __post_init__(self) -> None:
        if self.target_offset < -1:
            raise InvalidOffsetError(
                self.target_offset,
                "target_offset must be >= -1",
            )
        if not self.batch_id:
            raise ValueError("batch_id cannot be empty")
        if len(self.message_ids) != len(self.dedup_records):
            raise ValueError(
                "message_ids and dedup_records must have the same length"
            )


@dataclass
class ReplayResult:
    start_offset: int
    end_offset: int
    total_messages: int
    processed_count: int
    duplicate_count: int
    skipped_count: int
    replayed_dedup_records: list[DedupRecord] = field(default_factory=list)

    @property
    def processed_new_count(self) -> int:
        return self.processed_count

    @property
    def new_dedup_count(self) -> int:
        return len(self.replayed_dedup_records)
