from __future__ import annotations


class MicroBatchError(Exception):
    pass


class InvalidConfigError(MicroBatchError):
    pass


class BufferClosedError(MicroBatchError):
    pass


class BatchFlushError(MicroBatchError):
    def __init__(self, batch: list, attempts: int, last_error: Exception | None = None) -> None:
        self.batch = batch
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Batch flush failed after {attempts} attempts, "
            f"batch size: {len(batch)}, last error: {last_error}"
        )
