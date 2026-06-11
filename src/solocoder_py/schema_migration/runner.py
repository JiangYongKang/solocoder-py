from __future__ import annotations

from typing import Dict, List, Optional

from .exceptions import (
    MigrationExecutionError,
    MigrationNotFoundError,
    MigrationOrderError,
)
from .models import (
    IdempotencyCheckResult,
    Migration,
    MigrationResult,
    SchemaState,
)


class MigrationRunner:
    def __init__(self, schema_state: Optional[SchemaState] = None) -> None:
        self._state: SchemaState = schema_state or SchemaState()
        self._migrations: Dict[int, Migration] = {}

    @property
    def state(self) -> SchemaState:
        return self._state

    @property
    def current_version(self) -> int:
        return self._state.current_version

    def register_migration(self, migration: Migration) -> None:
        if migration.version in self._migrations:
            raise MigrationOrderError(
                f"Migration version {migration.version} is already registered"
            )
        self._migrations[migration.version] = migration

    def register_migrations(self, migrations: List[Migration]) -> None:
        for migration in migrations:
            self.register_migration(migration)

    def get_pending_migrations(self, target_version: Optional[int] = None) -> List[Migration]:
        current = self._state.current_version
        max_version = target_version if target_version is not None else max(self._migrations.keys()) if self._migrations else 0

        if max_version < current:
            raise MigrationOrderError(
                f"Target version {max_version} is lower than current version {current}"
            )

        pending = []
        for version in sorted(self._migrations.keys()):
            if version > current and version <= max_version:
                pending.append(self._migrations[version])

        self._validate_migration_chain(pending, current, max_version)
        return pending

    def _validate_migration_chain(
        self, pending: List[Migration], current: int, target: int
    ) -> None:
        if not pending:
            return

        expected_version = current + 1
        for migration in pending:
            if migration.version != expected_version:
                raise MigrationOrderError(
                    f"Migration chain broken: expected version {expected_version}, "
                    f"but got {migration.version}. "
                    f"Cannot skip intermediate migrations."
                )
            expected_version += 1

        if expected_version - 1 != target:
            missing = expected_version
            raise MigrationNotFoundError(
                f"Migration version {missing} required to reach target version {target} is missing"
            )

    def upgrade(self, target_version: Optional[int] = None) -> MigrationResult:
        if not self._migrations:
            return MigrationResult(
                success=True,
                from_version=self._state.current_version,
                to_version=self._state.current_version,
            )

        effective_target = (
            target_version if target_version is not None else max(self._migrations.keys())
        )

        if self._state.current_version == effective_target:
            return MigrationResult(
                success=True,
                from_version=self._state.current_version,
                to_version=self._state.current_version,
            )

        try:
            pending = self.get_pending_migrations(effective_target)
        except (MigrationOrderError, MigrationNotFoundError) as e:
            return MigrationResult(
                success=False,
                from_version=self._state.current_version,
                to_version=self._state.current_version,
                error_message=str(e),
            )

        if not pending:
            return MigrationResult(
                success=True,
                from_version=self._state.current_version,
                to_version=self._state.current_version,
            )

        return self._execute_migrations(pending)

    def _execute_migrations(self, migrations: List[Migration]) -> MigrationResult:
        applied: List[Migration] = []
        from_version = self._state.current_version
        idempotency_errors: List[str] = []

        for migration in migrations:
            try:
                idempotency_check = self._execute_with_idempotency_check(migration)
                if not idempotency_check.passed:
                    idempotency_errors.extend(idempotency_check.differences)
                    self._rollback_migrations(applied)
                    return MigrationResult(
                        success=False,
                        from_version=from_version,
                        to_version=from_version,
                        applied_versions=[m.version for m in applied],
                        rolled_back_versions=[m.version for m in applied],
                        failed_version=migration.version,
                        error_message=(
                            f"Migration {migration.version} failed idempotency check: "
                            + "; ".join(idempotency_check.differences)
                        ),
                        idempotency_errors=idempotency_errors,
                    )

                self._state.mark_applied(migration)
                applied.append(migration)

            except Exception as e:
                rollback_result = self._rollback_migrations(applied)
                return MigrationResult(
                    success=False,
                    from_version=from_version,
                    to_version=from_version,
                    applied_versions=[m.version for m in applied],
                    rolled_back_versions=[m.version for m in applied],
                    failed_version=migration.version,
                    error_message=str(e),
                    rollback_errors=rollback_result,
                )

        return MigrationResult(
            success=True,
            from_version=from_version,
            to_version=self._state.current_version,
            applied_versions=[m.version for m in applied],
        )

    def _execute_with_idempotency_check(self, migration: Migration) -> IdempotencyCheckResult:
        state_before_any = self._state.snapshot_data()

        try:
            migration.up(self._state.data)
        except Exception:
            self._restore_data(state_before_any)
            raise

        state_after_first = self._state.snapshot_data()

        try:
            migration.up(self._state.data)
        except Exception:
            self._restore_data(state_after_first)
            raise

        state_after_second = self._state.snapshot_data()

        differences = self._compare_states(state_after_first, state_after_second)

        self._restore_data(state_after_first)

        return IdempotencyCheckResult(
            passed=len(differences) == 0,
            first_state=state_after_first,
            second_state=state_after_second,
            differences=differences,
        )

    def _compare_states(self, state1: Dict, state2: Dict, path: str = "") -> List[str]:
        differences: List[str] = []

        all_keys = set(state1.keys()) | set(state2.keys())
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key not in state1:
                differences.append(f"{current_path}: missing in first state, present in second")
                continue
            if key not in state2:
                differences.append(f"{current_path}: present in first state, missing in second")
                continue

            val1 = state1[key]
            val2 = state2[key]

            if isinstance(val1, dict) and isinstance(val2, dict):
                differences.extend(self._compare_states(val1, val2, current_path))
            elif isinstance(val1, list) and isinstance(val2, list):
                if val1 != val2:
                    differences.append(f"{current_path}: lists differ - {val1} vs {val2}")
            else:
                if val1 != val2:
                    differences.append(f"{current_path}: values differ - {val1!r} vs {val2!r}")

        return differences

    def _restore_data(self, snapshot: Dict) -> None:
        self._state.data.clear()
        self._state.data.update(snapshot)

    def _rollback_migrations(self, migrations: List[Migration]) -> List[Dict]:
        rollback_errors: List[Dict] = []
        reversed_migrations = list(reversed(migrations))

        for migration in reversed_migrations:
            try:
                migration.down(self._state.data)
                self._state.mark_rolled_back(migration)
            except Exception as e:
                rollback_errors.append({
                    "version": migration.version,
                    "name": migration.name,
                    "error": str(e),
                })

        return rollback_errors

    def get_migration(self, version: int) -> Migration:
        if version not in self._migrations:
            raise MigrationNotFoundError(f"Migration version {version} not found")
        return self._migrations[version]

    def has_migration(self, version: int) -> bool:
        return version in self._migrations

    @property
    def latest_available_version(self) -> int:
        return max(self._migrations.keys()) if self._migrations else 0

    @property
    def registered_versions(self) -> List[int]:
        return sorted(self._migrations.keys())
