from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar
from collections.abc import Sequence

from .exceptions import InvalidConfigError

T = TypeVar("T")


class BatchStatus(str, Enum):
    PENDING = "pending"
    FLUSHING = "flushing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BatchRecord(Generic[T]):
    batch_id: int
    items: list[T]
    status: BatchStatus
    created_at: float
    flushed_at: float | None = None
    attempts: int = 0
    last_error: Exception | None = None

    def __repr__(self) -> str:
        return (
            f"BatchRecord(batch_id={self.batch_id}, size={len(self.items)}, "
            f"status={self.status.value}, attempts={self.attempts})"
        )


@dataclass
class MicroBatchConfig:
    max_size: int = 100
    max_interval: float = 5.0
    max_retries: int = 3
    retry_interval: float = 1.0
    scheduler_interval: float = 0.1

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.max_size < 1:
            raise InvalidConfigError("max_size must be at least 1")
        if self.max_interval <= 0:
            raise InvalidConfigError("max_interval must be positive")
        if self.max_retries < 0:
            raise InvalidConfigError("max_retries must be non-negative")
        if self.retry_interval < 0:
            raise InvalidConfigError("retry_interval must be non-negative")
        if self.scheduler_interval <= 0:
            raise InvalidConfigError("scheduler_interval must be positive")

    def __repr__(self) -> str:
        return (
            f"MicroBatchConfig(max_size={self.max_size}, "
            f"max_interval={self.max_interval}, "
            f"max_retries={self.max_retries}, "
            f"retry_interval={self.retry_interval}, "
            f"scheduler_interval={self.scheduler_interval})"
        )


class FlushResult:
    SUCCESS = "success"
    FAILURE = "failure"

    def __init__(self, status: str, error: Exception | None = None) -> None:
        self.status = status
        self.error = error

    @property
    def is_success(self) -> bool:
        return self.status == FlushResult.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.status == FlushResult.FAILURE

    @classmethod
    def ok(cls) -> "FlushResult":
        return cls(status=cls.SUCCESS, error=None)

    @classmethod
    def fail(cls, error: Exception | None = None) -> "FlushResult":
        return cls(status=cls.FAILURE, error=error)

    def __repr__(self) -> str:
        if self.is_success:
            return "FlushResult(success)"
        return f"FlushResult(failure, error={self.error})"
