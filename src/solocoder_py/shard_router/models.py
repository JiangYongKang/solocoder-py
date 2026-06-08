from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WriteStatus(Enum):
    SINGLE = "single"
    DUAL = "dual"
    REDIRECT = "redirect"


@dataclass(frozen=True)
class ShardNode:
    node_id: str
    host: str = ""
    port: int = 0


@dataclass(frozen=True)
class SlotRange:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("start must be <= end")

    def contains(self, slot: int) -> bool:
        return self.start <= slot <= self.end

    def to_list(self) -> list[int]:
        return list(range(self.start, self.end + 1))


@dataclass(frozen=True)
class SlotAssignment:
    node_id: str
    slot_ranges: list[SlotRange]

    @property
    def total_slots(self) -> int:
        return sum(r.end - r.start + 1 for r in self.slot_ranges)


@dataclass(frozen=True)
class MigrationInfo:
    slot: int
    source_node_id: str
    target_node_id: str
    in_progress: bool


@dataclass(frozen=True)
class MigrationProgress:
    total_migrating: int
    completed_migrations: int
    in_progress_slots: list[MigrationInfo]


@dataclass(frozen=True)
class RouteResult:
    node_id: str
    slot: int
    migrating: bool = False
    migration_target: str | None = None


@dataclass(frozen=True)
class WriteResult:
    status: WriteStatus
    primary_node_id: str
    secondary_node_id: str | None = None
    slot: int = -1


@dataclass(frozen=True)
class RouterSnapshot:
    total_slots: int
    assigned_slots: int
    unassigned_slots: int
    nodes: list[ShardNode]
    assignments: dict[str, SlotAssignment]
    migrations: MigrationProgress
