import pytest
from typing import Any, Dict

from solocoder_py.schema_migration import (
    IdempotencyCheckResult,
    Migration,
    MigrationIdempotencyError,
    MigrationNotFoundError,
    MigrationOrderError,
    MigrationResult,
    MigrationRunner,
    MigrationStatus,
    SchemaState,
    SchemaMigrationError,
)
from .conftest import make_migration, make_runner, make_state


class TestMigrationModel:
    def test_migration_creation(self):
        migration = make_migration(1, "test_migration")
        assert migration.version == 1
        assert migration.name == "test_migration"
        assert migration.description == ""

    def test_migration_version_must_be_positive(self):
        with pytest.raises(ValueError, match="version must be a positive integer"):
            Migration(version=0, name="bad", up=lambda d: None, down=lambda d: None)
        with pytest.raises(ValueError, match="version must be a positive integer"):
            Migration(version=-1, name="bad", up=lambda d: None, down=lambda d: None)

    def test_migration_name_cannot_be_empty(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Migration(version=1, name="", up=lambda d: None, down=lambda d: None)


class TestSchemaState:
    def test_initial_state(self):
        state = make_state()
        assert state.current_version == 0
        assert state.applied_migrations == {}
        assert state.data == {}
        assert state.migration_history == []

    def test_snapshot_data_creates_deep_copy(self):
        state = make_state()
        state.data["nested"] = {"key": "value", "list": [1, 2, 3]}
        snapshot = state.snapshot_data()

        state.data["nested"]["key"] = "modified"
        state.data["nested"]["list"].append(4)

        assert snapshot["nested"]["key"] == "value"
        assert snapshot["nested"]["list"] == [1, 2, 3]

    def test_mark_applied_updates_state(self):
        state = make_state()
        m1 = make_migration(1, "first")
        m2 = make_migration(2, "second")

        state.mark_applied(m1)
        assert state.current_version == 1
        assert 1 in state.applied_migrations
        assert len(state.migration_history) == 1
        assert state.migration_history[0]["action"] == "apply"
        assert state.migration_history[0]["status"] == MigrationStatus.APPLIED.value

        state.mark_applied(m2)
        assert state.current_version == 2
        assert 2 in state.applied_migrations
        assert len(state.migration_history) == 2

    def test_mark_rolled_back_removes_migration(self):
        state = make_state()
        m1 = make_migration(1, "first")
        m2 = make_migration(2, "second")

        state.mark_applied(m1)
        state.mark_applied(m2)
        assert state.current_version == 2

        state.mark_rolled_back(m2)
        assert state.current_version == 1
        assert 2 not in state.applied_migrations

        state.mark_rolled_back(m1)
        assert state.current_version == 0
        assert state.applied_migrations == {}


class TestIdempotencyCheckResult:
    def test_passed_check_does_not_raise(self):
        result = IdempotencyCheckResult(
            passed=True, first_state={}, second_state={}, differences=[]
        )
        result.raise_if_failed(1)

    def test_failed_check_raises(self):
        result = IdempotencyCheckResult(
            passed=False,
            first_state={"a": 1},
            second_state={"a": 2},
            differences=["a: values differ - 1 vs 2"],
        )
        with pytest.raises(MigrationIdempotencyError, match="not idempotent"):
            result.raise_if_failed(1)


class TestMigrationRunnerRegistration:
    def test_register_single_migration(self):
        runner = make_runner()
        migration = make_migration(1, "first")
        runner.register_migration(migration)
        assert runner.has_migration(1)
        assert runner.get_migration(1) is migration

    def test_register_duplicate_version_raises(self):
        runner = make_runner()
        runner.register_migration(make_migration(1, "first"))
        with pytest.raises(MigrationOrderError, match="already registered"):
            runner.register_migration(make_migration(1, "duplicate"))

    def test_register_multiple_migrations(self):
        runner = make_runner()
        migrations = [
            make_migration(1, "first"),
            make_migration(2, "second"),
            make_migration(3, "third"),
        ]
        runner.register_migrations(migrations)
        assert runner.registered_versions == [1, 2, 3]

    def test_get_migration_not_found_raises(self):
        runner = make_runner()
        with pytest.raises(MigrationNotFoundError):
            runner.get_migration(999)


class TestNormalUpgradeFlow:
    def test_upgrade_multiple_versions_success(self):
        runner = make_runner()
        runner.register_migrations([
            make_migration(1, "add_users"),
            make_migration(2, "add_products"),
            make_migration(3, "add_orders"),
        ])

        result = runner.upgrade()

        assert result.success is True
        assert result.from_version == 0
        assert result.to_version == 3
        assert result.applied_versions == [1, 2, 3]
        assert result.rolled_back_versions == []
        assert result.failed_version is None
        assert result.was_partial is False

        assert runner.current_version == 3
        assert runner.state.data["applied_count"] == 3
        assert runner.state.data["applied_v1"] is True
        assert runner.state.data["applied_v2"] is True
        assert runner.state.data["applied_v3"] is True
        assert runner.state.data["applied_versions"] == {1, 2, 3}

    def test_upgrade_from_version_2_to_5(self):
        state = make_state()
        state.current_version = 2
        state.data["applied_v1"] = True
        state.data["applied_v2"] = True
        state.data["applied_versions"] = {1, 2}
        state.data["applied_count"] = 2

        runner = make_runner(state)
        runner.register_migrations([
            make_migration(1, "first"),
            make_migration(2, "second"),
            make_migration(3, "third"),
            make_migration(4, "fourth"),
            make_migration(5, "fifth"),
        ])

        result = runner.upgrade()

        assert result.success is True
        assert result.from_version == 2
        assert result.to_version == 5
        assert result.applied_versions == [3, 4, 5]

    def test_upgrade_to_specific_target_version(self):
        runner = make_runner()
        runner.register_migrations([
            make_migration(1, "one"),
            make_migration(2, "two"),
            make_migration(3, "three"),
            make_migration(4, "four"),
        ])

        result = runner.upgrade(target_version=2)

        assert result.success is True
        assert result.to_version == 2
        assert result.applied_versions == [1, 2]
        assert runner.current_version == 2


class TestBoundaryConditions:
    def test_single_pending_migration(self):
        runner = make_runner()
        runner.register_migration(make_migration(1, "only_one"))

        result = runner.upgrade()

        assert result.success is True
        assert result.applied_versions == [1]
        assert result.to_version == 1
        assert runner.current_version == 1

    def test_already_latest_version_no_migration_needed(self):
        state = make_state()
        state.current_version = 3
        runner = make_runner(state)
        runner.register_migrations([
            make_migration(1, "one"),
            make_migration(2, "two"),
            make_migration(3, "three"),
        ])

        result = runner.upgrade()

        assert result.success is True
        assert result.from_version == 3
        assert result.to_version == 3
        assert result.applied_versions == []

    def test_empty_migration_list(self):
        runner = make_runner()

        result = runner.upgrade()

        assert result.success is True
        assert result.from_version == 0
        assert result.to_version == 0
        assert result.applied_versions == []

    def test_get_pending_migrations_empty_when_at_latest(self):
        state = make_state()
        state.current_version = 2
        runner = make_runner(state)
        runner.register_migrations([
            make_migration(1, "one"),
            make_migration(2, "two"),
        ])
        pending = runner.get_pending_migrations()
        assert pending == []

    def test_latest_available_version(self):
        runner = make_runner()
        assert runner.latest_available_version == 0

        runner.register_migration(make_migration(3, "three"))
        runner.register_migration(make_migration(1, "one"))
        assert runner.latest_available_version == 3


class TestMigrationOrderValidation:
    def test_skip_migration_version_raises(self):
        runner = make_runner()
        runner.register_migrations([
            make_migration(1, "one"),
            make_migration(3, "three"),
        ])

        result = runner.upgrade()
        assert result.success is False
        assert "chain broken" in result.error_message

    def test_target_version_lower_than_current_raises(self):
        state = make_state()
        state.current_version = 5
        runner = make_runner(state)
        runner.register_migrations([
            make_migration(1, "one"),
            make_migration(2, "two"),
        ])

        with pytest.raises(MigrationOrderError, match="lower than current version"):
            runner.get_pending_migrations()


class TestMigrationFailureAndRollback:
    def test_middle_migration_failure_triggers_reverse_rollback(self):
        execution_order: list[str] = []

        def make_failing_migration(version: int, fail: bool = False) -> Migration:
            def up(data: Dict[str, Any]) -> None:
                execution_order.append(f"v{version}_up")
                if fail:
                    raise RuntimeError(f"Migration {version} intentionally failed")
                data[f"applied_v{version}"] = True

            def down(data: Dict[str, Any]) -> None:
                execution_order.append(f"v{version}_down")
                data.pop(f"applied_v{version}", None)

            return Migration(
                version=version,
                name=f"migration_{version}",
                up=up,
                down=down,
            )

        runner = make_runner()
        runner.register_migrations([
            make_failing_migration(1),
            make_failing_migration(2),
            make_failing_migration(3, fail=True),
            make_failing_migration(4),
        ])

        result = runner.upgrade()

        assert result.success is False
        assert result.failed_version == 3
        assert result.from_version == 0
        assert result.to_version == 0
        assert result.was_partial is True
        assert result.applied_versions == [1, 2]
        assert result.rollback_attempted_versions == [1, 2]
        assert result.rolled_back_versions == [2, 1]
        assert result.successfully_rolled_back_versions == [2, 1]
        assert result.failed_rollback_versions == []

        assert runner.current_version == 0
        assert "applied_v1" not in runner.state.data
        assert "applied_v2" not in runner.state.data

        assert execution_order == [
            "v1_up", "v1_up",
            "v2_up", "v2_up",
            "v3_up",
            "v2_down", "v1_down",
        ]

    def test_rollback_order_is_reverse_of_apply_order(self):
        rollback_order: list[int] = []

        def make_tracked_migration(version: int, fail: bool = False) -> Migration:
            def up(data: Dict[str, Any]) -> None:
                if fail:
                    raise RuntimeError(f"Fail at v{version}")
                data[f"v{version}"] = True

            def down(data: Dict[str, Any]) -> None:
                rollback_order.append(version)

            return Migration(
                version=version,
                name=f"v{version}",
                up=up,
                down=down,
            )

        runner = make_runner()
        runner.register_migrations([
            make_tracked_migration(1),
            make_tracked_migration(2),
            make_tracked_migration(3),
            make_tracked_migration(4, fail=True),
        ])

        runner.upgrade()
        assert rollback_order == [3, 2, 1]


class TestIdempotencyValidation:
    def test_idempotent_migration_passes_check(self):
        def idempotent_up(data: Dict[str, Any]) -> None:
            data["users_table"] = True
            data.setdefault("user_count", 0)

        def idempotent_down(data: Dict[str, Any]) -> None:
            data.pop("users_table", None)
            data.pop("user_count", None)

        migration = Migration(
            version=1,
            name="idempotent",
            up=idempotent_up,
            down=idempotent_down,
        )

        runner = make_runner()
        runner.register_migration(migration)

        result = runner.upgrade()
        assert result.success is True
        assert result.idempotency_errors == []

    def test_non_idempotent_migration_fails_check(self):
        call_count = {"up": 0}

        def non_idempotent_up(data: Dict[str, Any]) -> None:
            call_count["up"] += 1
            if "counter" not in data:
                data["counter"] = 0
            data["counter"] += 1

        def non_idempotent_down(data: Dict[str, Any]) -> None:
            if "counter" in data and data["counter"] > 0:
                data["counter"] -= 1

        migration = Migration(
            version=1,
            name="non_idempotent",
            up=non_idempotent_up,
            down=non_idempotent_down,
        )

        runner = make_runner()
        runner.register_migration(migration)

        result = runner.upgrade()
        assert result.success is False
        assert result.failed_version == 1
        assert "counter" in result.error_message
        assert runner.current_version == 0

    def test_non_idempotent_migration_triggers_rollback(self):
        rollback_called = {"v1": False, "v2": False}

        def make_non_idempotent(version: int, bad: bool = False) -> Migration:
            def up(data: Dict[str, Any]) -> None:
                if bad:
                    if "bad_counter" not in data:
                        data["bad_counter"] = 0
                    data["bad_counter"] += 1
                else:
                    data[f"v{version}_applied"] = True

            def down(data: Dict[str, Any]) -> None:
                rollback_called[f"v{version}"] = True
                data.pop(f"v{version}_applied", None)
                if bad:
                    data.pop("bad_counter", None)

            return Migration(
                version=version,
                name=f"v{version}",
                up=up,
                down=down,
            )

        runner = make_runner()
        runner.register_migrations([
            make_non_idempotent(1),
            make_non_idempotent(2, bad=True),
        ])

        result = runner.upgrade()
        assert result.success is False
        assert result.failed_version == 2
        assert result.was_partial is True
        assert rollback_called["v1"] is True
        assert runner.current_version == 0


class TestRollbackFailureHandling:
    def test_rollback_failure_collects_errors(self):
        def make_migration_with_bad_rollback(
            version: int,
            fail_up: bool = False,
            fail_down: bool = False,
        ) -> Migration:
            def up(data: Dict[str, Any]) -> None:
                if fail_up:
                    raise RuntimeError(f"Up failed at v{version}")
                data[f"applied_v{version}"] = True

            def down(data: Dict[str, Any]) -> None:
                if fail_down:
                    raise RuntimeError(f"Down failed at v{version}")
                data.pop(f"applied_v{version}", None)

            return Migration(
                version=version,
                name=f"migration_{version}",
                up=up,
                down=down,
            )

        runner = make_runner()
        runner.register_migrations([
            make_migration_with_bad_rollback(1, fail_down=True),
            make_migration_with_bad_rollback(2, fail_down=True),
            make_migration_with_bad_rollback(3, fail_up=True),
        ])

        result = runner.upgrade()

        assert result.success is False
        assert result.had_rollback_failures is True
        assert len(result.rollback_errors) == 2

        error_versions = [e["version"] for e in result.rollback_errors]
        assert sorted(error_versions) == [1, 2]

    def test_mixed_rollback_success_and_failure(self):
        successful_rollbacks: list[int] = []

        def make_migration(version: int, fail_up: bool, fail_down: bool) -> Migration:
            def up(data: Dict[str, Any]) -> None:
                if fail_up:
                    raise RuntimeError("Up failed")
                data[f"v{version}"] = True

            def down(data: Dict[str, Any]) -> None:
                if fail_down:
                    raise RuntimeError("Down failed")
                successful_rollbacks.append(version)
                data.pop(f"v{version}", None)

            return Migration(
                version=version,
                name=f"v{version}",
                up=up,
                down=down,
            )

        runner = make_runner()
        runner.register_migrations([
            make_migration(1, fail_up=False, fail_down=False),
            make_migration(2, fail_up=False, fail_down=True),
            make_migration(3, fail_up=False, fail_down=False),
            make_migration(4, fail_up=True, fail_down=False),
        ])

        result = runner.upgrade()
        assert result.success is False
        assert result.had_rollback_failures is True
        assert len(result.rollback_errors) == 1
        assert result.rollback_errors[0]["version"] == 2
        assert successful_rollbacks == [3, 1]


class TestComplexDataTransformations:
    def test_schema_data_transformations(self):
        def up_v1(data: Dict[str, Any]) -> None:
            data["users"] = []

        def down_v1(data: Dict[str, Any]) -> None:
            data.pop("users", None)

        def up_v2(data: Dict[str, Any]) -> None:
            data["products"] = []
            if "users" in data:
                data["user_count"] = len(data["users"])

        def down_v2(data: Dict[str, Any]) -> None:
            data.pop("products", None)
            data.pop("user_count", None)

        def up_v3(data: Dict[str, Any]) -> None:
            data["orders"] = []
            data["schema_version"] = 3

        def down_v3(data: Dict[str, Any]) -> None:
            data.pop("orders", None)
            data.pop("schema_version", None)

        runner = make_runner()
        runner.register_migrations([
            Migration(version=1, name="add_users", up=up_v1, down=down_v1),
            Migration(version=2, name="add_products", up=up_v2, down=down_v2),
            Migration(version=3, name="add_orders", up=up_v3, down=down_v3),
        ])

        result = runner.upgrade()
        assert result.success is True
        assert runner.state.data == {
            "users": [],
            "products": [],
            "orders": [],
            "user_count": 0,
            "schema_version": 3,
        }


class TestMigrationResultProperties:
    def test_migration_result_properties(self):
        result = MigrationResult(
            success=True,
            from_version=0,
            to_version=5,
            applied_versions=[1, 2, 3, 4, 5],
        )
        assert result.was_partial is False
        assert result.had_rollback_failures is False
        assert result.rollback_attempted_versions == []
        assert result.rolled_back_versions == []
        assert result.successfully_rolled_back_versions == []
        assert result.failed_rollback_versions == []

        partial_result = MigrationResult(
            success=False,
            from_version=0,
            to_version=0,
            applied_versions=[1, 2],
            rollback_attempted_versions=[1, 2],
            rolled_back_versions=[2, 1],
            failed_version=3,
        )
        assert partial_result.was_partial is True
        assert partial_result.had_rollback_failures is False
        assert partial_result.rollback_attempted_versions == [1, 2]
        assert partial_result.successfully_rolled_back_versions == [2, 1]
        assert partial_result.failed_rollback_versions == []

        partial_with_errors = MigrationResult(
            success=False,
            from_version=0,
            to_version=0,
            applied_versions=[1, 2, 3],
            rollback_attempted_versions=[1, 2, 3],
            rolled_back_versions=[3, 1],
            failed_version=4,
            rollback_errors=[{"version": 2, "error": "failed"}],
        )
        assert partial_with_errors.was_partial is True
        assert partial_with_errors.had_rollback_failures is True
        assert partial_with_errors.rollback_attempted_versions == [1, 2, 3]
        assert partial_with_errors.successfully_rolled_back_versions == [3, 1]
        assert partial_with_errors.failed_rollback_versions == [2]


class TestStateCompare:
    def test_compare_equal_states(self):
        runner = make_runner()
        state1 = {"a": 1, "b": {"c": [1, 2, 3]}}
        state2 = {"a": 1, "b": {"c": [1, 2, 3]}}
        diffs = runner._compare_states(state1, state2)
        assert diffs == []

    def test_compare_different_values(self):
        runner = make_runner()
        state1 = {"a": 1}
        state2 = {"a": 2}
        diffs = runner._compare_states(state1, state2)
        assert len(diffs) == 1
        assert "a:" in diffs[0]

    def test_compare_missing_keys(self):
        runner = make_runner()
        state1 = {"a": 1}
        state2 = {"a": 1, "b": 2}
        diffs = runner._compare_states(state1, state2)
        assert len(diffs) == 1
        assert "b:" in diffs[0]
        assert "missing in first" in diffs[0]

    def test_compare_nested_dicts(self):
        runner = make_runner()
        state1 = {"outer": {"inner": 1}}
        state2 = {"outer": {"inner": 2}}
        diffs = runner._compare_states(state1, state2)
        assert len(diffs) == 1
        assert "outer.inner:" in diffs[0]

    def test_compare_lists(self):
        runner = make_runner()
        state1 = {"list": [1, 2, 3]}
        state2 = {"list": [1, 2, 4]}
        diffs = runner._compare_states(state1, state2)
        assert len(diffs) == 1
        assert "list:" in diffs[0]


class TestHistoryTracking:
    def test_migration_history_tracking(self):
        runner = make_runner()
        runner.register_migrations([
            make_migration(1, "first"),
            make_migration(2, "second"),
        ])

        runner.upgrade()

        history = runner.state.migration_history
        assert len(history) == 2
        assert history[0]["version"] == 1
        assert history[0]["action"] == "apply"
        assert history[0]["status"] == MigrationStatus.APPLIED.value
        assert history[1]["version"] == 2
        assert history[1]["action"] == "apply"

    def test_rollback_history_tracking(self):
        def make_failing(version: int, fail: bool) -> Migration:
            def up(data: Dict[str, Any]) -> None:
                if fail:
                    raise RuntimeError("fail")
                data[f"v{version}"] = True

            def down(data: Dict[str, Any]) -> None:
                data.pop(f"v{version}", None)

            return Migration(
                version=version, name=f"v{version}", up=up, down=down
            )

        runner = make_runner()
        runner.register_migrations([
            make_failing(1, False),
            make_failing(2, False),
            make_failing(3, True),
        ])

        runner.upgrade()

        history = runner.state.migration_history
        actions = [(h["version"], h["action"]) for h in history]
        assert actions == [
            (1, "apply"),
            (2, "apply"),
            (2, "rollback"),
            (1, "rollback"),
        ]


class TestRegressionFixes:
    def test_idempotency_failure_includes_rollback_errors(self):
        def make_non_idempotent_with_bad_rollback(
            version: int, non_idempotent: bool, fail_down: bool
        ) -> Migration:
            call_tracker = {"count": 0}

            def up(data: Dict[str, Any]) -> None:
                call_tracker["count"] += 1
                if non_idempotent:
                    data.setdefault("bad_counter", 0)
                    data["bad_counter"] += 1
                else:
                    data[f"v{version}"] = True

            def down(data: Dict[str, Any]) -> None:
                if fail_down:
                    raise RuntimeError(f"Rollback v{version} failed")
                data.pop(f"v{version}", None)
                data.pop("bad_counter", None)

            return Migration(
                version=version,
                name=f"v{version}",
                up=up,
                down=down,
            )

        runner = make_runner()
        runner.register_migrations([
            make_non_idempotent_with_bad_rollback(1, False, True),
            make_non_idempotent_with_bad_rollback(2, False, False),
            make_non_idempotent_with_bad_rollback(3, True, False),
        ])

        result = runner.upgrade()
        assert result.success is False
        assert result.failed_version == 3
        assert len(result.idempotency_errors) > 0

        assert result.had_rollback_failures is True
        assert len(result.rollback_errors) >= 1
        rollback_failed_versions = [e["version"] for e in result.rollback_errors]
        assert 1 in rollback_failed_versions

        assert result.rollback_attempted_versions == [1, 2]
        assert 2 in result.rolled_back_versions
        assert 1 not in result.rolled_back_versions

    def test_idempotency_failure_restores_to_original_state(self):
        state_before_up = {"preexisting": "value"}
        runner_state = make_state()
        runner_state.data.update(state_before_up)

        runner = make_runner(runner_state)

        call_count = {"up": 0}

        def non_idempotent_up(data: Dict[str, Any]) -> None:
            call_count["up"] += 1
            data.setdefault("side_effect_counter", 0)
            data["side_effect_counter"] += 1

        def down(data: Dict[str, Any]) -> None:
            data.pop("side_effect_counter", None)

        runner.register_migration(Migration(
            version=1, name="bad", up=non_idempotent_up, down=down
        ))

        result = runner.upgrade()
        assert result.success is False
        assert result.failed_version == 1

        assert runner.state.data == state_before_up
        assert "side_effect_counter" not in runner.state.data
        assert runner_state.current_version == 0
        assert 1 not in runner_state.applied_migrations

    def test_second_up_exception_restores_to_original_state(self):
        call_count = {"up": 0}
        state_before = {"existing_key": "existing_value"}
        runner_state = make_state()
        runner_state.data.update(state_before)

        def second_up_fails(data: Dict[str, Any]) -> None:
            call_count["up"] += 1
            if call_count["up"] == 1:
                data["first_up_side_effect"] = "should_be_removed"
            else:
                raise RuntimeError("Second up intentionally fails")

        def down(data: Dict[str, Any]) -> None:
            data.pop("first_up_side_effect", None)

        runner = make_runner(runner_state)
        runner.register_migration(Migration(
            version=1, name="second_up_fails", up=second_up_fails, down=down
        ))

        result = runner.upgrade()
        assert result.success is False
        assert result.failed_version == 1
        assert "Second up intentionally fails" in result.error_message

        assert runner.state.data == state_before
        assert "first_up_side_effect" not in runner.state.data
        assert runner.current_version == 0
        assert 1 not in runner_state.applied_migrations

    def test_rolled_back_versions_accurately_reflects_success(self):
        def make_migration(
            version: int, fail_up: bool, fail_down: bool
        ) -> Migration:
            def up(data: Dict[str, Any]) -> None:
                if fail_up:
                    raise RuntimeError(f"Up v{version} failed")
                data[f"v{version}"] = True

            def down(data: Dict[str, Any]) -> None:
                if fail_down:
                    raise RuntimeError(f"Down v{version} failed")
                data.pop(f"v{version}", None)

            return Migration(
                version=version, name=f"v{version}", up=up, down=down
            )

        runner = make_runner()
        runner.register_migrations([
            make_migration(1, False, True),
            make_migration(2, False, False),
            make_migration(3, False, True),
            make_migration(4, False, False),
            make_migration(5, True, False),
        ])

        result = runner.upgrade()
        assert result.success is False
        assert result.failed_version == 5

        assert result.rollback_attempted_versions == [1, 2, 3, 4]

        assert set(result.rolled_back_versions) == {4, 2}
        assert len(result.rolled_back_versions) == 2

        assert set(result.failed_rollback_versions) == {3, 1}
        assert len(result.rollback_errors) == 2

        failed_versions_in_errors = [e["version"] for e in result.rollback_errors]
        assert sorted(failed_versions_in_errors) == [1, 3]

        assert result.applied_versions == [1, 2, 3, 4]
