from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .exceptions import (
    InvalidBufferConfigError,
    InvalidWindowConfigError,
)


class LateDataStrategy(str, Enum):
    LOG = "log"
    DISCARD = "discard"
    CALLBACK = "callback"


class FlushReason(str, Enum):
    BATCH_SIZE = "batch_size"
    TIMEOUT = "timeout"
    MANUAL = "manual"


@dataclass
class BufferConfig:
    batch_size: int = 100
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise InvalidBufferConfigError("batch_size must be at least 1")
        if self.timeout_seconds < 0:
            raise InvalidBufferConfigError("timeout_seconds must be non-negative")


@dataclass
class SchemaConfig:
    field_mapping: dict[str, str] = field(default_factory=dict)
    drop_unmapped: bool = False


@dataclass
class WindowConfig:
    tolerance_seconds: float = 30.0
    timestamp_field: str = "timestamp"
    late_data_strategy: LateDataStrategy = LateDataStrategy.LOG

    def __post_init__(self) -> None:
        if self.tolerance_seconds < 0:
            raise InvalidWindowConfigError("tolerance_seconds must be non-negative")


@dataclass
class FlushResult:
    batch: list[dict[str, Any]]
    reason: FlushReason
    flushed_at: float = 0.0
    batch_id: int = 0


@dataclass
class ProcessedBatch:
    data: list[dict[str, Any]]
    late_data: list[dict[str, Any]]
    original_count: int = 0
