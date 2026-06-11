from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .exceptions import MigrationIdempotencyError


class MigrationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    version: int
    name: str
    up: Callable[[Dict[str, Any]], None]
    down: Callable[[Dict[str, Any]], None]
    checksum: Optional[str] = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("version must be a positive integer")
        if not self.name:
            raise ValueError("name cannot be empty")


@dataclass
class SchemaState:
    current_version: int = 0
    applied_migrations: Dict[int, Migration] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    migration_history: List[Dict[str, Any]] = field(default_factory=list)

    def snapshot_data(self) -> Dict[str, Any]:
        return self._deep_copy(self.data)

    def _deep_copy(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        if isinstance(obj, set):
            return {self._deep_copy(item) for item in obj}
        return obj

    def mark_applied(self, migration: Migration) -> None:
        self.applied_migrations[migration.version] = migration
        self.current_version = max(self.current_version, migration.version)
        self.migration_history.append({
            "version": migration.version,
            "name": migration.name,
            "action": "apply",
            "status": MigrationStatus.APPLIED.value,
        })

    def mark_rolled_back(self, migration: Migration) -> None:
        if migration.version in self.applied_migrations:
            del self.applied_migrations[migration.version]
        versions = sorted(self.applied_migrations.keys())
        self.current_version = versions[-1] if versions else 0
        self.migration_history.append({
            "version": migration.version,
            "name": migration.name,
            "action": "rollback",
            "status": MigrationStatus.ROLLED_BACK.value,
        })


@dataclass
class MigrationResult:
    success: bool
    from_version: int
    to_version: int
    applied_versions: List[int] = field(default_factory=list)
    rollback_attempted_versions: List[int] = field(default_factory=list)
    rolled_back_versions: List[int] = field(default_factory=list)
    failed_version: Optional[int] = None
    error_message: str = ""
    idempotency_errors: List[str] = field(default_factory=list)
    rollback_errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def was_partial(self) -> bool:
        return len(self.rollback_attempted_versions) > 0

    @property
    def had_rollback_failures(self) -> bool:
        return len(self.rollback_errors) > 0

    @property
    def successfully_rolled_back_versions(self) -> List[int]:
        return self.rolled_back_versions

    @property
    def failed_rollback_versions(self) -> List[int]:
        return [err["version"] for err in self.rollback_errors]


@dataclass
class IdempotencyCheckResult:
    passed: bool
    first_state: Dict[str, Any]
    second_state: Dict[str, Any]
    differences: List[str] = field(default_factory=list)

    def raise_if_failed(self, version: int) -> None:
        if not self.passed:
            diffs = "; ".join(self.differences)
            raise MigrationIdempotencyError(
                f"Migration version {version} is not idempotent. Differences: {diffs}"
            )
