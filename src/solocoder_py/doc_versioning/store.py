from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..three_way_merge import merge_texts
from .diff_utils import apply_diff, apply_diffs_sequential, compute_diff
from .exceptions import (
    BaseVersionMismatchError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    InvalidVersionError,
    VersionNotFoundError,
)
from .models import (
    CommitResult,
    DocumentDiff,
    DocumentInfo,
    DocumentVersion,
    MergeStatus,
    VersionType,
)


class _DocumentRecord:
    def __init__(self, document_id: str, created_at: datetime) -> None:
        self.document_id = document_id
        self.created_at = created_at
        self.updated_at = created_at
        self.versions: Dict[int, DocumentVersion] = {}
        self.latest_version: int = 0
        self._baseline_version: int = 0

    @property
    def version_count(self) -> int:
        return len(self.versions)

    def add_version(self, version: DocumentVersion) -> None:
        self.versions[version.version] = version
        if version.version > self.latest_version:
            self.latest_version = version.version
        if version.is_baseline and self._baseline_version == 0:
            self._baseline_version = version.version
        self.updated_at = version.created_at

    def get_baseline_version(self) -> int:
        return self._baseline_version


class DocumentVersionStore:
    def __init__(self) -> None:
        self._documents: Dict[str, _DocumentRecord] = {}
        self._next_version_counter: Dict[str, int] = {}

    def _get_record(self, document_id: str) -> _DocumentRecord:
        if document_id not in self._documents:
            raise DocumentNotFoundError(f"Document '{document_id}' not found")
        return self._documents[document_id]

    def _next_version(self, document_id: str) -> int:
        current = self._next_version_counter.get(document_id, 0)
        next_ver = current + 1
        self._next_version_counter[document_id] = next_ver
        return next_ver

    def create_document(self, document_id: str, content: str) -> CommitResult:
        if document_id in self._documents:
            raise DocumentAlreadyExistsError(
                f"Document '{document_id}' already exists"
            )

        now = datetime.now()
        record = _DocumentRecord(document_id, now)
        self._documents[document_id] = record
        self._next_version_counter[document_id] = 0

        version_num = self._next_version(document_id)
        version = DocumentVersion(
            version=version_num,
            content=content,
            version_type=VersionType.BASELINE,
            created_at=now,
            parent_version=None,
        )
        record.add_version(version)

        return CommitResult(
            document_id=document_id,
            new_version=version_num,
            base_version=0,
            merge_status=MergeStatus.CLEAN,
            conflict_count=0,
        )

    def get_latest_version(self, document_id: str) -> int:
        record = self._get_record(document_id)
        return record.latest_version

    def get_version(self, document_id: str, version: int) -> DocumentVersion:
        record = self._get_record(document_id)

        if version < 1 or version > record.latest_version:
            raise VersionNotFoundError(
                f"Version {version} not found for document '{document_id}'. "
                f"Latest version: {record.latest_version}"
            )

        if version not in record.versions:
            raise VersionNotFoundError(
                f"Version {version} not found for document '{document_id}'"
            )

        ver = record.versions[version]
        if ver.content is not None:
            return ver

        content = self._reconstruct_content(record, version)
        ver.content = content
        return ver

    def get_version_content(self, document_id: str, version: int) -> str:
        ver = self.get_version(document_id, version)
        return ver.content

    def _reconstruct_content(self, record: _DocumentRecord, target_version: int) -> str:
        baseline_ver = record.get_baseline_version()
        if baseline_ver == 0:
            raise InvalidVersionError("No baseline version found")

        baseline = record.versions[baseline_ver]
        if baseline.content is None:
            raise InvalidVersionError("Baseline version has no content")

        if target_version == baseline_ver:
            return baseline.content

        diffs: List[DocumentDiff] = []
        current = baseline_ver + 1
        while current <= target_version:
            ver = record.versions[current]
            if ver.diff is None:
                if ver.content is not None:
                    return ver.content
                raise InvalidVersionError(
                    f"Version {current} has no diff and no content"
                )
            diffs.append(ver.diff)
            current += 1

        return apply_diffs_sequential(baseline.content, diffs)

    def commit_version(self, document_id: str, content: str,
                       base_version: Optional[int] = None) -> CommitResult:
        record = self._get_record(document_id)
        latest = record.latest_version

        if base_version is None:
            base_version = latest

        if base_version < 1 or base_version > latest:
            raise BaseVersionMismatchError(
                f"Invalid base version {base_version}. "
                f"Latest version: {latest}"
            )

        if base_version == latest:
            return self._commit_incremental(record, content, base_version)
        else:
            return self._commit_with_merge(record, content, base_version)

    def _commit_incremental(self, record: _DocumentRecord, content: str,
                            base_version: int) -> CommitResult:
        base_content = self.get_version_content(record.document_id, base_version)
        diff = compute_diff(base_content, content, base_version, 0)

        new_version_num = self._next_version(record.document_id)
        now = datetime.now()

        version = DocumentVersion(
            version=new_version_num,
            content=None,
            diff=diff,
            version_type=VersionType.INCREMENTAL,
            created_at=now,
            parent_version=base_version,
        )
        version.diff.target_version = new_version_num

        record.add_version(version)

        return CommitResult(
            document_id=record.document_id,
            new_version=new_version_num,
            base_version=base_version,
            merge_status=MergeStatus.CLEAN,
            conflict_count=0,
        )

    def _commit_with_merge(self, record: _DocumentRecord, content: str,
                           base_version: int) -> CommitResult:
        base_content = self.get_version_content(record.document_id, base_version)
        latest_content = self.get_version_content(record.document_id, record.latest_version)

        merge_result = merge_texts(base_content, content, latest_content)

        new_version_num = self._next_version(record.document_id)
        now = datetime.now()
        merged_text = merge_result.get_merged_text()
        diff = compute_diff(latest_content, merged_text, record.latest_version, 0)
        diff.target_version = new_version_num

        has_conflicts = merge_result.has_conflicts
        merge_status = MergeStatus.CONFLICTED if has_conflicts else MergeStatus.CLEAN
        conflict_count = merge_result.conflict_count if has_conflicts else 0
        version_content = merged_text if has_conflicts else None

        version = DocumentVersion(
            version=new_version_num,
            content=version_content,
            diff=diff,
            version_type=VersionType.MERGED,
            created_at=now,
            parent_version=record.latest_version,
            merge_status=merge_status,
            merge_source_a=base_version,
            merge_source_b=record.latest_version,
        )

        record.add_version(version)

        return CommitResult(
            document_id=record.document_id,
            new_version=new_version_num,
            base_version=base_version,
            merge_status=merge_status,
            conflict_count=conflict_count,
        )

    def list_versions(self, document_id: str) -> List[DocumentVersion]:
        record = self._get_record(document_id)
        return [record.versions[v] for v in sorted(record.versions.keys())]

    def get_document_info(self, document_id: str) -> DocumentInfo:
        record = self._get_record(document_id)
        return DocumentInfo(
            document_id=document_id,
            latest_version=record.latest_version,
            version_count=record.version_count,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def document_exists(self, document_id: str) -> bool:
        return document_id in self._documents

    def get_diff_between_versions(self, document_id: str,
                                   from_version: int, to_version: int) -> DocumentDiff:
        from_content = self.get_version_content(document_id, from_version)
        to_content = self.get_version_content(document_id, to_version)
        return compute_diff(from_content, to_content, from_version, to_version)

    def rollback_to_version(self, document_id: str, target_version: int) -> CommitResult:
        record = self._get_record(document_id)

        if target_version < 1 or target_version > record.latest_version:
            raise VersionNotFoundError(
                f"Version {target_version} not found for document '{document_id}'"
            )

        target_content = self.get_version_content(document_id, target_version)
        return self.commit_version(document_id, target_content, record.latest_version)
