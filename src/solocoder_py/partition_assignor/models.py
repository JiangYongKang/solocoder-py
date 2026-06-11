from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConsumerStatus(str, Enum):
    ACTIVE = "active"
    LEAVING = "leaving"


@dataclass(frozen=True)
class Partition:
    partition_id: int

    def __post_init__(self) -> None:
        if self.partition_id < 0:
            raise ValueError("partition_id must be non-negative")


@dataclass
class Consumer:
    consumer_id: str
    status: ConsumerStatus = ConsumerStatus.ACTIVE
    assigned_partitions: set[int] = field(default_factory=set)
    last_heartbeat: float = 0.0

    def __post_init__(self) -> None:
        if not self.consumer_id:
            raise ValueError("consumer_id must not be empty")


@dataclass(frozen=True)
class AssignmentChange:
    consumer_id: str
    assigned_partitions: list[int]
    revoked_partitions: list[int]


@dataclass(frozen=True)
class RebalanceResult:
    generation_id: int
    assignments: dict[str, list[int]]
    changes: list[AssignmentChange]
    orphan_partitions_recovered: list[int] = field(default_factory=list)
    heartbeat_timeout_orphans_recovered: list[int] = field(default_factory=list)
