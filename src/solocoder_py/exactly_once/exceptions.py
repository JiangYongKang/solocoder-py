from __future__ import annotations


class ExactlyOnceError(Exception):
    pass


class MessageNotFoundError(ExactlyOnceError):
    def __init__(self, offset: int) -> None:
        self.offset = offset
        super().__init__(f"Message not found at offset {offset}")


class CheckpointNotFoundError(ExactlyOnceError):
    def __init__(self) -> None:
        super().__init__("No checkpoint found, starting from beginning")


class DedupStoreOverflowError(ExactlyOnceError):
    def __init__(self, max_size: int) -> None:
        self.max_size = max_size
        super().__init__(
            f"Dedup store has exceeded maximum capacity of {max_size} entries"
        )


class InvalidOffsetError(ExactlyOnceError):
    def __init__(self, offset: int, reason: str) -> None:
        self.offset = offset
        self.reason = reason
        super().__init__(f"Invalid offset {offset}: {reason}")


class AtomicCommitInterruptedError(ExactlyOnceError):
    def __init__(self, message_ids: list[str], offset: int) -> None:
        self.message_ids = message_ids
        self.offset = offset
        super().__init__(
            f"Atomic commit was interrupted before completing. "
            f"offset={offset}, pending message_ids={message_ids}"
        )


class OffsetSkipWarning(ExactlyOnceError):
    def __init__(self, expected_offset: int, actual_offset: int) -> None:
        self.expected_offset = expected_offset
        self.actual_offset = actual_offset
        super().__init__(
            f"Offset skip detected: expected next offset {expected_offset}, "
            f"but processed offset {actual_offset}. "
            f"Messages in between are skipped without processing."
        )


class CheckpointMonotonicityError(ExactlyOnceError):
    def __init__(self, new_offset: int, existing_offset: int) -> None:
        self.new_offset = new_offset
        self.existing_offset = existing_offset
        super().__init__(
            f"Checkpoint monotonicity violated: attempted to commit "
            f"offset {new_offset} but latest committed offset is "
            f"{existing_offset}"
        )
