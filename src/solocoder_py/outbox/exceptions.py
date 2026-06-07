from __future__ import annotations


class OutboxError(Exception):
    pass


class InvalidStateTransitionError(OutboxError):
    def __init__(self, current: "OutboxMessageState", target: "OutboxMessageState") -> None:
        from .states import OutboxMessageState

        self.current = current
        self.target = target
        super().__init__(
            f"Invalid state transition: {current.value} -> {target.value}"
        )


class MessageNotFoundError(OutboxError):
    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        super().__init__(f"Message not found: {message_id}")


class MessageAlreadyClaimedError(OutboxError):
    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        super().__init__(f"Message already claimed by another worker: {message_id}")


class AtomicWriteError(OutboxError):
    def __init__(self, message: str = "Atomic write failed") -> None:
        super().__init__(message)
