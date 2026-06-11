import abc

import pytest

from solocoder_py.data_migration import (
    BatchMigrationError,
    BatchInfo,
    BatchStatus,
    CheckpointStore,
    DataMigrationError,
    DataMigrator,
    InMemoryCheckpointStore,
    InvalidBatchSizeError,
    MigrationState,
    MigrationStatus,
    RollbackError,
)

from .conftest import make_migrator, make_source_data


class TestModels:
    def test_batch_info_validation(self):
        batch = BatchInfo(batch_index=0, start_index=0, end_index=10)
        assert batch.batch_index == 0
        assert batch.start_index == 0
        assert batch.end_index == 10
        assert batch.record_count == 10
        assert batch.status == BatchStatus.PENDING

    def test_batch_info_negative_batch_index(self):
        with pytest.raises(ValueError, match="batch_index must be non-negative"):
            BatchInfo(batch_index=-1, start_index=0, end_index=10)

    def test_batch_info_negative_start_index(self):
        with pytest.raises(ValueError, match="start_index must be non-negative"):
            BatchInfo(batch_index=0, start_index=-1, end_index=10)

    def test_batch_info_end_before_start(self):
        with pytest.raises(ValueError, match="end_index must be >= start_index"):
            BatchInfo(batch_index=0, start_index=10, end_index=5)

    def test_migration_state_initial(self):
        state = MigrationState()
        assert state.status == MigrationStatus.IDLE
        assert state.total_records == 0
        assert state.total_batches == 0
        assert state.completed_batches == 0
        assert state.checkpoint == -1
        assert state.is_completed is False
        assert state.is_failed is False
        assert state.is_rolled_back is False
        assert state.progress_percent == 0.0

    def test_migration_state_progress_percent(self):
        state = MigrationState(total_batches=10, completed_batches=5)
        assert state.progress_percent == 50.0

    def test_migration_state_get_batch(self):
        batches = [BatchInfo(batch_index=i, start_index=i * 10, end_index=(i + 1) * 10) for i in range(3)]
        state = MigrationState(total_batches=3, batches=batches)
        assert state.get_batch(0) is not None
        assert state.get_batch(0).batch_index == 0
        assert state.get_batch(2) is not None
        assert state.get_batch(3) is None
        assert state.get_batch(-1) is None


class TestDataMigratorInitialization:
    def test_invalid_batch_size_zero(self):
        with pytest.raises(InvalidBatchSizeError, match="batch_size must be positive"):
            DataMigrator(source_data=[], batch_size=0)

    def test_invalid_batch_size_negative(self):
        with pytest.raises(InvalidBatchSizeError, match="batch_size must be positive"):
            DataMigrator(source_data=[], batch_size=-5)

    def test_initial_state_empty_source(self):
        migrator = DataMigrator(source_data=[], batch_size=10)
        state = migrator.state
        assert state.status == MigrationStatus.IDLE
        assert state.total_records == 0
        assert state.total_batches == 0
        assert state.completed_batches == 0
        assert len(state.batches) == 0

    def test_initial_state_with_data(self):
        source = make_source_data(25)
        migrator = make_migrator(source, batch_size=10)
        state = migrator.state
        assert state.total_records == 25
        assert state.total_batches == 3
        assert len(state.batches) == 3
        assert state.batches[0].start_index == 0
        assert state.batches[0].end_index == 10
        assert state.batches[1].start_index == 10
        assert state.batches[1].end_index == 20
        assert state.batches[2].start_index == 20
        assert state.batches[2].end_index == 25


class TestNormalMigrationFlow:
    def test_full_migration_success(self):
        source = make_source_data(25)
        migrator = make_migrator(source, batch_size=10)

        state = migrator.migrate()

        assert state.status == MigrationStatus.COMPLETED
        assert state.completed_batches == 3
        assert state.checkpoint == 2
        assert len(migrator.target_data) == 25

        for i in range(25):
            assert i in migrator.target_data
            assert migrator.target_data[i]["name"] == f"record-{i}"

    def test_migration_batch_statuses(self):
        source = make_source_data(25)
        migrator = make_migrator(source, batch_size=10)

        migrator.migrate()
        state = migrator.state

        for batch in state.batches:
            assert batch.status == BatchStatus.COMPLETED

    def test_step_by_step_migration(self):
        source = make_source_data(25)
        migrator = make_migrator(source, batch_size=10)

        assert migrator.migrate_next_batch() is True
        state = migrator.state
        assert state.completed_batches == 1
        assert state.checkpoint == 0
        assert len(migrator.target_data) == 10

        assert migrator.migrate_next_batch() is True
        state = migrator.state
        assert state.completed_batches == 2
        assert state.checkpoint == 1
        assert len(migrator.target_data) == 20

        assert migrator.migrate_next_batch() is True
        state = migrator.state
        assert state.completed_batches == 3
        assert state.checkpoint == 2
        assert state.status == MigrationStatus.COMPLETED
        assert len(migrator.target_data) == 25

        assert migrator.migrate_next_batch() is False

    def test_exact_batch_size_division(self):
        source = make_source_data(30)
        migrator = make_migrator(source, batch_size=10)

        state = migrator.migrate()

        assert state.total_batches == 3
        assert state.completed_batches == 3
        for batch in state.batches:
            assert batch.record_count == 10
        assert len(migrator.target_data) == 30

    def test_last_batch_partial(self):
        source = make_source_data(23)
        migrator = make_migrator(source, batch_size=10)

        state = migrator.migrate()

        assert state.total_batches == 3
        assert state.batches[0].record_count == 10
        assert state.batches[1].record_count == 10
        assert state.batches[2].record_count == 3
        assert len(migrator.target_data) == 23

    def test_single_batch_migration(self):
        source = make_source_data(5)
        migrator = make_migrator(source, batch_size=100)

        state = migrator.migrate()

        assert state.total_batches == 1
        assert state.completed_batches == 1
        assert state.batches[0].record_count == 5
        assert len(migrator.target_data) == 5

    def test_get_batch_records(self):
        source = make_source_data(25)
        migrator = make_migrator(source, batch_size=10)

        batch0 = migrator.get_batch_records(0)
        assert len(batch0) == 10
        assert batch0[0]["id"] == 0

        batch2 = migrator.get_batch_records(2)
        assert len(batch2) == 5
        assert batch2[0]["id"] == 20

        assert migrator.get_batch_records(-1) == []
        assert migrator.get_batch_records(100) == []


class TestEmptySourceMigration:
    def test_empty_source_migrate(self):
        migrator = make_migrator([], batch_size=10)

        state = migrator.migrate()

        assert state.status == MigrationStatus.COMPLETED
        assert state.total_records == 0
        assert state.total_batches == 0
        assert state.completed_batches == 0
        assert len(migrator.target_data) == 0

    def test_empty_source_next_batch(self):
        migrator = make_migrator([], batch_size=10)

        result = migrator.migrate_next_batch()

        assert result is False
        assert migrator.state.status == MigrationStatus.COMPLETED

    def test_empty_source_rollback(self):
        migrator = make_migrator([], batch_size=10)

        state = migrator.rollback()

        assert state.status == MigrationStatus.ROLLED_BACK
        assert len(migrator.target_data) == 0


class TestCheckpointAndResume:
    def test_checkpoint_saved_after_each_batch(self):
        source = make_source_data(30)
        checkpoint_store = InMemoryCheckpointStore()
        migrator = make_migrator(source, batch_size=10, checkpoint_store=checkpoint_store)

        migrator.migrate_next_batch()
        assert checkpoint_store.load() == 0

        migrator.migrate_next_batch()
        assert checkpoint_store.load() == 1

        migrator.migrate_next_batch()
        assert checkpoint_store.load() == 2

    def test_resume_from_checkpoint_same_instance(self):
        source = make_source_data(30)
        checkpoint_store = InMemoryCheckpointStore()
        migrator = make_migrator(source, batch_size=10, checkpoint_store=checkpoint_store)

        migrator.migrate_next_batch()
        migrator.migrate_next_batch()
        assert migrator.state.checkpoint == 1
        assert migrator.state.completed_batches == 2
        assert len(migrator.target_data) == 20

        state = migrator.resume_from_checkpoint()

        assert state.status == MigrationStatus.COMPLETED
        assert state.completed_batches == 3
        assert state.checkpoint == 2
        assert len(migrator.target_data) == 30

    def test_resume_with_new_instance_and_persisted_target(self):
        source = make_source_data(30)
        checkpoint_store = InMemoryCheckpointStore()
        target_store = {}

        migrator1 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
        )

        migrator1.migrate_next_batch()
        migrator1.migrate_next_batch()
        assert migrator1.state.checkpoint == 1
        assert len(target_store) == 20

        migrator2 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
        )

        state = migrator2.resume_from_checkpoint()

        assert state.status == MigrationStatus.COMPLETED
        assert state.completed_batches == 3
        assert state.checkpoint == 2
        assert len(target_store) == 30
        for i in range(30):
            assert i in target_store

    def test_resume_completed_migration(self):
        source = make_source_data(20)
        checkpoint_store = InMemoryCheckpointStore()
        migrator1 = make_migrator(source, batch_size=10, checkpoint_store=checkpoint_store)
        migrator1.migrate()

        migrator2 = make_migrator(source, batch_size=10, checkpoint_store=checkpoint_store)
        state = migrator2.resume_from_checkpoint()

        assert state.status == MigrationStatus.COMPLETED
        assert state.completed_batches == 2

    def test_resume_no_checkpoint_starts_from_beginning(self):
        source = make_source_data(20)
        checkpoint_store = InMemoryCheckpointStore()
        migrator = make_migrator(source, batch_size=10, checkpoint_store=checkpoint_store)

        state = migrator.resume_from_checkpoint()

        assert state.status == MigrationStatus.COMPLETED
        assert state.completed_batches == 2

    def test_checkpoint_cleared_on_reset(self):
        source = make_source_data(20)
        checkpoint_store = InMemoryCheckpointStore()
        migrator = make_migrator(source, batch_size=10, checkpoint_store=checkpoint_store)

        migrator.migrate()
        assert checkpoint_store.load() == 1

        migrator.reset()
        assert checkpoint_store.load() == -1
        assert migrator.state.status == MigrationStatus.IDLE
        assert len(migrator.target_data) == 0


class TestFailureAndRollback:
    def test_middle_batch_failure(self):
        source = make_source_data(30)
        fail_count = [0]

        def failing_migrator(records):
            for record in records:
                if record["id"] == 15:
                    fail_count[0] += 1
                    raise RuntimeError("Simulated failure at record 15")

        migrator = make_migrator(source, batch_size=10, batch_migrator=failing_migrator)

        with pytest.raises(BatchMigrationError) as exc_info:
            migrator.migrate()

        assert exc_info.value.batch_index == 1

        state = migrator.state
        assert state.status == MigrationStatus.FAILED
        assert state.failed_batch_index == 1
        assert state.completed_batches == 1
        assert state.batches[0].status == BatchStatus.COMPLETED
        assert state.batches[1].status == BatchStatus.FAILED
        assert state.batches[2].status == BatchStatus.PENDING

    def test_full_rollback_after_failure(self):
        source = make_source_data(30)
        target_store = {}
        fail_count = [0]

        def failing_migrator(records):
            if records and records[0]["id"] == 10 and fail_count[0] == 0:
                fail_count[0] += 1
                raise RuntimeError("Simulated failure at batch 1")
            for record in records:
                target_store[record["id"]] = record

        migrator = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            id_extractor=lambda r: r["id"],
            batch_migrator=failing_migrator,
        )

        with pytest.raises(BatchMigrationError) as exc_info:
            migrator.migrate()

        assert exc_info.value.batch_index == 1
        assert len(target_store) == 10

        state = migrator.rollback()

        assert state.status == MigrationStatus.ROLLED_BACK
        assert state.completed_batches == 0
        assert state.checkpoint == -1
        assert len(target_store) == 0
        for batch in state.batches:
            if batch.status == BatchStatus.FAILED:
                continue
            assert batch.status in (BatchStatus.ROLLED_BACK, BatchStatus.PENDING)

    def test_rollback_all_completed_batches(self):
        source = make_source_data(25)
        migrator = make_migrator(source, batch_size=10)

        migrator.migrate()
        assert len(migrator.target_data) == 25

        state = migrator.rollback()

        assert state.status == MigrationStatus.ROLLED_BACK
        assert state.completed_batches == 0
        assert state.checkpoint == -1
        assert len(migrator.target_data) == 0
        for batch in state.batches:
            assert batch.status == BatchStatus.ROLLED_BACK

    def test_step_by_step_rollback(self):
        source = make_source_data(25)
        migrator = make_migrator(source, batch_size=10)

        migrator.migrate()
        assert len(migrator.target_data) == 25

        assert migrator.rollback_next_batch() is True
        assert len(migrator.target_data) == 20
        assert migrator.state.checkpoint == 1

        assert migrator.rollback_next_batch() is True
        assert len(migrator.target_data) == 10
        assert migrator.state.checkpoint == 0

        assert migrator.rollback_next_batch() is True
        assert len(migrator.target_data) == 0
        assert migrator.state.checkpoint == -1
        assert migrator.state.status == MigrationStatus.ROLLED_BACK

        assert migrator.rollback_next_batch() is False

    def test_rollback_empty_migration(self):
        migrator = make_migrator([], batch_size=10)

        state = migrator.rollback()

        assert state.status == MigrationStatus.ROLLED_BACK
        assert len(migrator.target_data) == 0

    def test_first_batch_failure(self):
        source = make_source_data(20)

        def failing_migrator(records):
            raise RuntimeError("First batch fails")

        migrator = make_migrator(source, batch_size=10, batch_migrator=failing_migrator)

        with pytest.raises(BatchMigrationError) as exc_info:
            migrator.migrate()

        assert exc_info.value.batch_index == 0

        state = migrator.state
        assert state.completed_batches == 0
        assert state.checkpoint == -1
        assert len(migrator.target_data) == 0

    def test_rollback_after_full_migration(self):
        source = make_source_data(20)
        migrator = make_migrator(source, batch_size=10)

        migrator.migrate()
        assert len(migrator.target_data) == 20

        state = migrator.rollback()

        assert state.status == MigrationStatus.ROLLED_BACK
        assert len(migrator.target_data) == 0


class TestResumeAfterFailure:
    def test_resume_from_failed_state_triggers_rollback(self):
        source = make_source_data(30)
        target_store = {}
        checkpoint_store = InMemoryCheckpointStore()
        fail_count = [0]

        def failing_migrator(records):
            for record in records:
                if record["id"] == 10 and fail_count[0] == 0:
                    fail_count[0] += 1
                    raise RuntimeError("Simulated failure")
                target_store[record["id"]] = record

        migrator1 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
            batch_migrator=failing_migrator,
        )

        with pytest.raises(BatchMigrationError):
            migrator1.migrate()

        assert migrator1.state.status == MigrationStatus.FAILED
        assert migrator1.state.checkpoint == 0
        assert len(target_store) == 10

        migrator2 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
            batch_migrator=failing_migrator,
        )

        assert migrator2.state.status == MigrationStatus.IDLE

        state = migrator2.resume_from_checkpoint()

        assert state.status == MigrationStatus.ROLLED_BACK
        assert state.completed_batches == 0
        assert state.checkpoint == -1
        assert len(target_store) == 0


class TestRollbackInterruptionAndResume:
    def test_rollback_interrupted_then_resumed(self):
        source = make_source_data(30)
        target_store = {}
        rollback_fail_count = [0]
        checkpoint_store = InMemoryCheckpointStore()

        def failing_rollbacker(records):
            if records and records[0]["id"] == 10 and rollback_fail_count[0] == 0:
                rollback_fail_count[0] += 1
                raise RuntimeError("Rollback failure at batch 1")
            for record in records:
                if record["id"] in target_store:
                    del target_store[record["id"]]

        migrator1 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
            batch_rollbacker=failing_rollbacker,
        )

        migrator1.migrate()
        assert len(target_store) == 30

        with pytest.raises(RollbackError) as exc_info:
            migrator1.rollback()

        assert exc_info.value.batch_index == 1

        state = migrator1.state
        assert state.completed_batches == 2
        assert state.checkpoint == 1
        assert len(target_store) == 20
        assert state.batches[2].status == BatchStatus.ROLLED_BACK
        assert state.batches[1].status == BatchStatus.COMPLETED
        assert state.batches[0].status == BatchStatus.COMPLETED

        migrator2 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
            batch_rollbacker=failing_rollbacker,
        )

        state2 = migrator2.resume_rollback_from_checkpoint()

        assert state2.status == MigrationStatus.ROLLED_BACK
        assert state2.completed_batches == 0
        assert state2.checkpoint == -1
        assert len(target_store) == 0


class TestComplexScenarios:
    def test_migrate_rollback_migrate_again(self):
        source = make_source_data(20)
        migrator = make_migrator(source, batch_size=10)

        migrator.migrate()
        assert len(migrator.target_data) == 20

        migrator.rollback()
        assert len(migrator.target_data) == 0

        migrator.reset()
        state = migrator.migrate()

        assert state.status == MigrationStatus.COMPLETED
        assert len(migrator.target_data) == 20

    def test_custom_id_extractor(self):
        source = [
            {"user_id": "u1", "name": "Alice"},
            {"user_id": "u2", "name": "Bob"},
            {"user_id": "u3", "name": "Charlie"},
        ]
        migrator = DataMigrator(
            source_data=source,
            batch_size=2,
            id_extractor=lambda r: r["user_id"],
        )

        migrator.migrate()

        assert len(migrator.target_data) == 3
        assert "u1" in migrator.target_data
        assert "u2" in migrator.target_data
        assert "u3" in migrator.target_data

    def test_custom_batch_migrator_and_rollbacker(self):
        source = make_source_data(20)
        migrated_records = []
        rolled_back_records = []

        def custom_migrator(records):
            for r in records:
                migrated_records.append(r["id"])

        def custom_rollbacker(records):
            for r in records:
                rolled_back_records.append(r["id"])

        migrator = make_migrator(
            source,
            batch_size=10,
            batch_migrator=custom_migrator,
            batch_rollbacker=custom_rollbacker,
        )

        migrator.migrate()
        assert len(migrated_records) == 20
        assert migrated_records == list(range(20))

        migrator.rollback()
        assert len(rolled_back_records) == 20
        expected_rollback = list(range(10, 20)) + list(range(10))
        assert rolled_back_records == expected_rollback

    def test_large_batch_size_single_batch(self):
        source = make_source_data(5)
        migrator = make_migrator(source, batch_size=1000)

        state = migrator.migrate()

        assert state.total_batches == 1
        assert state.completed_batches == 1
        assert state.batches[0].record_count == 5
        assert len(migrator.target_data) == 5

    def test_progress_percent_during_migration(self):
        source = make_source_data(100)
        migrator = make_migrator(source, batch_size=20)

        migrator.migrate_next_batch()
        assert migrator.state.progress_percent == 20.0

        migrator.migrate_next_batch()
        assert migrator.state.progress_percent == 40.0

        migrator.migrate()
        assert migrator.state.progress_percent == 100.0


class TestErrorCases:
    def test_batch_migration_error_attributes(self):
        err = BatchMigrationError(5, "test error")
        assert err.batch_index == 5
        assert "Batch 5" in str(err)
        assert "test error" in str(err)

    def test_rollback_error_attributes(self):
        err = RollbackError(3, "rollback failed")
        assert err.batch_index == 3
        assert "Batch 3" in str(err)
        assert "rollback failed" in str(err)

    def test_data_migration_error_base_class(self):
        assert issubclass(BatchMigrationError, DataMigrationError)
        assert issubclass(RollbackError, DataMigrationError)
        assert issubclass(InvalidBatchSizeError, DataMigrationError)

    def test_migrate_twice_completed_stays_completed(self):
        source = make_source_data(10)
        migrator = make_migrator(source, batch_size=10)

        migrator.migrate()
        state = migrator.migrate()

        assert state.status == MigrationStatus.COMPLETED
        assert state.completed_batches == 1

    def test_rollback_twice_stays_rolled_back(self):
        source = make_source_data(10)
        migrator = make_migrator(source, batch_size=10)

        migrator.migrate()
        migrator.rollback()
        state = migrator.rollback()

        assert state.status == MigrationStatus.ROLLED_BACK


class TestInMemoryCheckpointStore:
    def test_initial_checkpoint(self):
        store = InMemoryCheckpointStore()
        assert store.load() == -1

    def test_save_and_load(self):
        store = InMemoryCheckpointStore()
        state = MigrationState(checkpoint=5)
        store.save(5, state)
        assert store.load() == 5

    def test_clear(self):
        store = InMemoryCheckpointStore()
        state = MigrationState(checkpoint=3)
        store.save(3, state)
        assert store.load() == 3
        store.clear()
        assert store.load() == -1

    def test_load_state(self):
        store = InMemoryCheckpointStore()
        state = MigrationState(total_records=100, checkpoint=2)
        store.save(2, state)

        loaded = store.load_state()
        assert loaded is not None
        assert loaded.total_records == 100
        assert loaded.checkpoint == 2

    def test_load_state_none_when_empty(self):
        store = InMemoryCheckpointStore()
        assert store.load_state() is None

    def test_save_and_load_state_independence(self):
        store = InMemoryCheckpointStore()
        state = MigrationState(total_records=10)
        store.save(0, state)

        loaded = store.load_state()
        loaded.total_records = 999

        reloaded = store.load_state()
        assert reloaded.total_records == 10


class TestCheckpointStoreABCEnforcement:
    def test_incomplete_subclass_cannot_instantiate(self):
        class IncompleteStore(CheckpointStore):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteStore()

    def test_partial_subclass_cannot_instantiate(self):
        class PartialStore(CheckpointStore):
            def save(self, checkpoint, state):
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PartialStore()

    def test_complete_subclass_can_instantiate(self):
        class CompleteStore(CheckpointStore):
            def __init__(self):
                self._data = {}

            def save(self, checkpoint, state):
                self._data["checkpoint"] = checkpoint
                self._data["state"] = state

            def load(self):
                return self._data.get("checkpoint", -1)

            def load_state(self):
                return self._data.get("state")

            def clear(self):
                self._data.clear()

        store = CompleteStore()
        assert store is not None

    def test_inmemory_store_is_subclass_of_abc(self):
        assert issubclass(InMemoryCheckpointStore, CheckpointStore)
        assert issubclass(CheckpointStore, abc.ABC)


class TestFailureRecoveryNoWriteBeforeRollback:
    def test_resume_from_failed_state_does_not_write_before_rollback(self):
        source = make_source_data(30)
        target_store = {}
        checkpoint_store = InMemoryCheckpointStore()
        fail_count = [0]
        write_count = [0]

        def tracking_migrator(records):
            for record in records:
                write_count[0] += 1
                if record["id"] == 10 and fail_count[0] == 0:
                    fail_count[0] += 1
                    raise RuntimeError("Simulated failure")
                target_store[record["id"]] = record

        migrator1 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
            batch_migrator=tracking_migrator,
        )

        with pytest.raises(BatchMigrationError):
            migrator1.migrate()

        writes_before_resume = write_count[0]
        assert len(target_store) == 10

        migrator2 = DataMigrator(
            source_data=source,
            target_store=target_store,
            batch_size=10,
            checkpoint_store=checkpoint_store,
            id_extractor=lambda r: r["id"],
            batch_migrator=tracking_migrator,
        )

        state = migrator2.resume_from_checkpoint()

        assert state.status == MigrationStatus.ROLLED_BACK
        assert len(target_store) == 0
        assert write_count[0] == writes_before_resume
