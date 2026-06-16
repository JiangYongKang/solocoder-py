from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ..three_way_merge import DiffHunk


class VersionType(str, Enum):
    BASELINE = "baseline"
    INCREMENTAL = "incremental"
    MERGED = "merged"


class MergeStatus(str, Enum):
    CLEAN = "clean"
    CONFLICTED = "conflicted"


@dataclass
class DocumentDiff:
    base_version: int
    target_version: int
    hunks: List[DiffHunk] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.hunks) == 0

    @property
    def hunk_count(self) -> int:
        return len(self.hunks)


@dataclass
class DocumentVersion:
    version: int
    content: Optional[str] = None
    diff: Optional[DocumentDiff] = None
    version_type: VersionType = VersionType.INCREMENTAL
    created_at: datetime = field(default_factory=datetime.now)
    parent_version: Optional[int] = None
    merge_status: Optional[MergeStatus] = None
    merge_source_a: Optional[int] = None
    merge_source_b: Optional[int] = None

    @property
    def is_baseline(self) -> bool:
        return self.version_type == VersionType.BASELINE

    @property
    def is_incremental(self) -> bool:
        return self.version_type == VersionType.INCREMENTAL

    @property
    def is_merged(self) -> bool:
        return self.version_type == VersionType.MERGED

    @property
    def has_conflict(self) -> bool:
        return self.merge_status == MergeStatus.CONFLICTED


@dataclass
class DocumentInfo:
    document_id: str
    latest_version: int
    version_count: int
    created_at: datetime
    updated_at: datetime

    @property
    def has_versions(self) -> bool:
        return self.version_count > 0


@dataclass
class CommitResult:
    document_id: str
    new_version: int
    base_version: int
    merge_status: MergeStatus
    conflict_count: int = 0
