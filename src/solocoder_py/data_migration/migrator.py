from __future__ import annotations

import copy
import threading
from typing import Any, Callable, Dict, List, Optional

from .exceptions import (
    BatchMigrationError,
    CheckpointError,
    DataMigrationError,
    InvalidBatchSizeError,
    RollbackError,
)
from .models import (
    BatchInfo,
    BatchStatus,
    MigrationState,
    MigrationStatus,
)


class CheckpointStore:
    def save(self, checkpoint: int, state: MigrationState) -> None:
        raise NotImplementedError

    def load(self) -> Optional[int]:
        raise NotImplementedError

    def load_state(self) -> Optional[MigrationState]:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class InMemoryCheckpointStore(CheckpointStore):
    def __init__(self) -> None:
        self._checkpoint: int = -1
        self._state: Optional[MigrationState] = None

    def save(self, checkpoint: int, state: MigrationState) -> None:
        self._checkpoint = checkpoint
        self._state = copy.deepcopy(state)

    def load(self) -> Optional[int]:
        return self._checkpoint

    def load_state(self) -> Optional[MigrationState]:
        return copy.deepcopy(self._state) if self._state else None

    def clear(self) -> None:
        self._checkpoint = -1
        self._state = None


class DataMigrator:
    def __init__(
        self,
        source_data: List[Any],
        target_store: Optional[Dict[Any, Any]] = None,
        batch_size: int = 100,
        checkpoint_store: Optional[CheckpointStore] = None,
        id_extractor: Optional[Callable[[Any], Any]] = None,
        batch_migrator: Optional[Callable[[List[Any]], None]] = None,
        batch_rollbacker: Optional[Callable[[List[Any]], None]] = None,
    ) -> None:
        if batch_size <= 0:
            raise InvalidBatchSizeError("batch_size must be positive")

        self._source_data: List[Any] = source_data
        self._target_store: Dict[Any, Any] = target_store if target_store is not None else {}
        self._batch_size: int = batch_size
        self._checkpoint_store: CheckpointStore = (
            checkpoint_store if checkpoint_store is not None else InMemoryCheckpointStore()
        )
        self._id_extractor: Callable[[Any], Any] = id_extractor or (lambda record: record.get("id") if isinstance(record, dict) else record)
        self._custom_batch_migrator = batch_migrator
        self._custom_batch_rollbacker = batch_rollbacker

        self._lock = threading.RLock()
        self._state: MigrationState = MigrationState()
        self._init_state()

    def _init_state(self) -> None:
        total_records = len(self._source_data)
        total_batches = (total_records + self._batch_size - 1) // self._batch_size if total_records > 0 else 0

        self._state = MigrationState(
            status=MigrationStatus.IDLE,
            total_records=total_records,
            batch_size=self._batch_size,
            total_batches=total_batches,
            completed_batches=0,
            batches=[],
            checkpoint=-1,
        )

        for i in range(total_batches):
            start = i * self._batch_size
            end = min(start + self._batch_size, total_records)
            self._state.batches.append(
                BatchInfo(
                    batch_index=i,
                    start_index=start,
                    end_index=end,
                    status=BatchStatus.PENDING,
                )
            )

    @property
    def state(self) -> MigrationState:
        with self._lock:
            return copy.deepcopy(self._state)

    @property
    def target_data(self) -> Dict[Any, Any]:
        with self._lock:
            return copy.deepcopy(self._target_store)

    def get_batch_records(self, batch_index: int) -> List[Any]:
        with self._lock:
            if batch_index < 0 or batch_index >= self._state.total_batches:
                return []
            batch_info = self._state.batches[batch_index]
            return self._source_data[batch_info.start_index : batch_info.end_index]

    def _save_checkpoint(self) -> None:
        try:
            self._checkpoint_store.save(self._state.checkpoint, self._state)
        except Exception as e:
            raise CheckpointError(f"Failed to save checkpoint: {e}") from e

    def _load_checkpoint(self) -> int:
        try:
            checkpoint = self._checkpoint_store.load()
            return checkpoint if checkpoint is not None else -1
        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint: {e}") from e

    def _migrate_batch(self, batch_index: int) -> None:
        batch_info = self._state.batches[batch_index]
        batch_info.status = BatchStatus.MIGRATING
        self._state.status = MigrationStatus.MIGRATING

        records = self._source_data[batch_info.start_index : batch_info.end_index]

        try:
            if self._custom_batch_migrator:
                self._custom_batch_migrator(records)
            else:
                for record in records:
                    record_id = self._id_extractor(record)
                    self._target_store[record_id] = record

            batch_info.status = BatchStatus.COMPLETED
            self._state.completed_batches += 1
            self._state.checkpoint = batch_index
            self._save_checkpoint()

        except Exception as e:
            batch_info.status = BatchStatus.FAILED
            batch_info.error_message = str(e)
            raise BatchMigrationError(batch_index, str(e)) from e

    def migrate(self) -> MigrationState:
        with self._lock:
            if self._state.total_records == 0:
                self._state.status = MigrationStatus.COMPLETED
                return self.state

            start_batch = self._state.checkpoint + 1

            if start_batch >= self._state.total_batches:
                if self._state.completed_batches == self._state.total_batches:
                    self._state.status = MigrationStatus.COMPLETED
                return self.state

            try:
                for batch_index in range(start_batch, self._state.total_batches):
                    self._migrate_batch(batch_index)

                self._state.status = MigrationStatus.COMPLETED
                self._state.failed_batch_index = None
                self._state.error_message = None

            except BatchMigrationError as e:
                self._state.status = MigrationStatus.FAILED
                self._state.failed_batch_index = e.batch_index
                self._state.error_message = str(e)
                self._save_checkpoint()
                raise

            return self.state

    def migrate_next_batch(self) -> bool:
        with self._lock:
            if self._state.total_records == 0:
                self._state.status = MigrationStatus.COMPLETED
                return False

            next_batch = self._state.checkpoint + 1

            if next_batch >= self._state.total_batches:
                if self._state.completed_batches == self._state.total_batches:
                    self._state.status = MigrationStatus.COMPLETED
                return False

            try:
                self._migrate_batch(next_batch)
                if next_batch == self._state.total_batches - 1:
                    self._state.status = MigrationStatus.COMPLETED
                return True
            except BatchMigrationError as e:
                self._state.status = MigrationStatus.FAILED
                self._state.failed_batch_index = e.batch_index
                self._state.error_message = str(e)
                self._save_checkpoint()
                raise

    def _rollback_batch(self, batch_index: int) -> None:
        batch_info = self._state.batches[batch_index]

        if batch_info.status != BatchStatus.COMPLETED and batch_info.status != BatchStatus.FAILED:
            return

        prev_status = batch_info.status
        batch_info.status = BatchStatus.MIGRATING
        self._state.status = MigrationStatus.ROLLING_BACK

        records = self._source_data[batch_info.start_index : batch_info.end_index]

        try:
            if self._custom_batch_rollbacker:
                self._custom_batch_rollbacker(records)
            else:
                for record in records:
                    record_id = self._id_extractor(record)
                    if record_id in self._target_store:
                        del self._target_store[record_id]

            batch_info.status = BatchStatus.ROLLED_BACK
            if prev_status == BatchStatus.COMPLETED:
                self._state.completed_batches -= 1
            self._state.checkpoint = batch_index - 1
            self._save_checkpoint()

        except Exception as e:
            batch_info.status = prev_status
            raise RollbackError(batch_index, str(e)) from e

    def rollback(self) -> MigrationState:
        with self._lock:
            if self._state.completed_batches == 0:
                self._state.status = MigrationStatus.ROLLED_BACK
                self._target_store.clear()
                return self.state

            last_completed = self._state.checkpoint

            try:
                for batch_index in range(last_completed, -1, -1):
                    if self._state.batches[batch_index].status in (
                        BatchStatus.COMPLETED,
                        BatchStatus.FAILED,
                    ):
                        self._rollback_batch(batch_index)

                self._state.status = MigrationStatus.ROLLED_BACK
                self._state.failed_batch_index = None
                self._state.error_message = None

            except RollbackError as e:
                self._state.status = MigrationStatus.FAILED
                self._state.failed_batch_index = e.batch_index
                self._state.error_message = str(e)
                self._save_checkpoint()
                raise

            return self.state

    def rollback_next_batch(self) -> bool:
        with self._lock:
            if self._state.checkpoint < 0:
                if self._state.status in (MigrationStatus.ROLLING_BACK, MigrationStatus.FAILED):
                    self._state.status = MigrationStatus.ROLLED_BACK
                return False

            batch_index = self._state.checkpoint

            if self._state.batches[batch_index].status not in (
                BatchStatus.COMPLETED,
                BatchStatus.FAILED,
            ):
                return False

            try:
                self._rollback_batch(batch_index)
                if self._state.checkpoint < 0:
                    self._state.status = MigrationStatus.ROLLED_BACK
                return True
            except RollbackError as e:
                self._state.status = MigrationStatus.FAILED
                self._state.failed_batch_index = e.batch_index
                self._state.error_message = str(e)
                self._save_checkpoint()
                raise

    def _restore_migration_state(self, checkpoint: int) -> None:
        if checkpoint < 0:
            return

        effective_checkpoint = min(checkpoint, self._state.total_batches - 1)
        if effective_checkpoint < 0:
            return

        for i in range(effective_checkpoint + 1):
            batch_info = self._state.batches[i]
            batch_info.status = BatchStatus.COMPLETED

            records = self._source_data[batch_info.start_index : batch_info.end_index]
            if self._custom_batch_migrator:
                self._custom_batch_migrator(records)
            else:
                for record in records:
                    record_id = self._id_extractor(record)
                    self._target_store[record_id] = record

        self._state.checkpoint = effective_checkpoint
        self._state.completed_batches = effective_checkpoint + 1

    def resume_from_checkpoint(self) -> MigrationState:
        with self._lock:
            checkpoint = self._load_checkpoint()
            if checkpoint < 0:
                return self.migrate()

            stored_state = None
            try:
                stored_state = self._checkpoint_store.load_state()
            except NotImplementedError:
                stored_state = None

            if stored_state and stored_state.status in (
                MigrationStatus.FAILED,
                MigrationStatus.ROLLING_BACK,
            ):
                self._restore_migration_state(checkpoint)
                if stored_state.failed_batch_index is not None:
                    failed_idx = stored_state.failed_batch_index
                    if 0 <= failed_idx < len(self._state.batches):
                        self._state.batches[failed_idx].status = BatchStatus.FAILED
                        self._state.batches[failed_idx].error_message = stored_state.batches[failed_idx].error_message
                return self.rollback()

            self._restore_migration_state(checkpoint)

            if checkpoint >= self._state.total_batches - 1:
                self._state.status = MigrationStatus.COMPLETED
                return self.state

            return self.migrate()

    def resume_rollback_from_checkpoint(self) -> MigrationState:
        with self._lock:
            checkpoint = self._load_checkpoint()

            if checkpoint < 0:
                self._state.status = MigrationStatus.ROLLED_BACK
                for batch in self._state.batches:
                    batch.status = BatchStatus.ROLLED_BACK
                return self.state

            self._restore_migration_state(checkpoint)

            for i in range(checkpoint + 1, self._state.total_batches):
                self._state.batches[i].status = BatchStatus.ROLLED_BACK

            return self.rollback()

    def reset(self) -> None:
        with self._lock:
            self._target_store.clear()
            self._checkpoint_store.clear()
            self._init_state()
