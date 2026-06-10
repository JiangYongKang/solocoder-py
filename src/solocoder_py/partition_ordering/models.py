from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MessageStatus(str, Enum):
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    COMMITTED = "committed"


@dataclass(frozen=True)
class Message:
    offset: int
    key: str
    value: Any
    partition_id: int
    timestamp: float

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.partition_id < 0:
            raise ValueError("partition_id must be non-negative")
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")


@dataclass
class PartitionOffset:
    partition_id: int
    committed_offset: int = -1
    last_pulled_offset: int = -1

    def __post_init__(self) -> None:
        if self.partition_id < 0:
            raise ValueError("partition_id must be non-negative")


@dataclass(frozen=True)
class ConsumerAssignment:
    consumer_id: str
    partition_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.consumer_id:
            raise ValueError("consumer_id must not be empty")


@dataclass(frozen=True)
class RebalanceEvent:
    consumer_id: str
    assigned_partitions: list[int]
    revoked_partitions: list[int]
    generation_id: int


@dataclass
class ConsumerState:
    consumer_id: str
    assigned_partitions: set[int] = field(default_factory=set)
    partition_offsets: dict[int, PartitionOffset] = field(default_factory=dict)
    in_flight_messages: dict[int, list[Message]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.consumer_id:
            raise ValueError("consumer_id must not be empty")

    def get_offset(self, partition_id: int) -> PartitionOffset:
        if partition_id not in self.partition_offsets:
            self.partition_offsets[partition_id] = PartitionOffset(partition_id=partition_id)
        return self.partition_offsets[partition_id]
