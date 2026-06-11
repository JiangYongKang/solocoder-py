from __future__ import annotations


class DataMigrationError(Exception):
    pass


class BatchMigrationError(DataMigrationError):
    def __init__(self, batch_index: int, message: str = "") -> None:
        self.batch_index = batch_index
        super().__init__(f"Batch {batch_index} migration failed: {message}")


class RollbackError(DataMigrationError):
    def __init__(self, batch_index: int, message: str = "") -> None:
        self.batch_index = batch_index
        super().__init__(f"Batch {batch_index} rollback failed: {message}")


class CheckpointError(DataMigrationError):
    pass


class InvalidBatchSizeError(DataMigrationError):
    pass
