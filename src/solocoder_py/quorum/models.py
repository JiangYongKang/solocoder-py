from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ReplicaStatus(str, Enum):
    ONLINE = "ONLINE"
    UNREACHABLE = "UNREACHABLE"


@dataclass
class StoredValue:
    value: Any
    version: int
    timestamp: float


@dataclass
class ReplicaStats:
    replica_id: str
    status: ReplicaStatus
    keys_count: int
    total_reads: int = 0
    successful_reads: int = 0
    total_writes: int = 0
    successful_writes: int = 0
    read_latencies_ms: list[float] = field(default_factory=list)
    write_latencies_ms: list[float] = field(default_factory=list)

    @property
    def read_success_rate(self) -> float:
        if self.total_reads == 0:
            return 0.0
        return self.successful_reads / self.total_reads

    @property
    def write_success_rate(self) -> float:
        if self.total_writes == 0:
            return 0.0
        return self.successful_writes / self.total_writes

    @property
    def avg_read_latency_ms(self) -> float:
        if not self.read_latencies_ms:
            return 0.0
        return sum(self.read_latencies_ms) / len(self.read_latencies_ms)

    @property
    def avg_write_latency_ms(self) -> float:
        if not self.write_latencies_ms:
            return 0.0
        return sum(self.write_latencies_ms) / len(self.write_latencies_ms)


@dataclass
class WriteResult:
    key: str
    value: Any
    version: int
    successful_replicas: list[str]
    failed_replicas: list[str]

    @property
    def success(self) -> bool:
        return len(self.successful_replicas) > 0


@dataclass
class ReadResult:
    key: str
    value: Any
    version: int
    successful_replicas: list[str]
    failed_replicas: list[str]
    repaired_replicas: list[str] = field(default_factory=list)
    conflict_detected: bool = False
    winning_value: Optional[StoredValue] = None

    @property
    def success(self) -> bool:
        return len(self.successful_replicas) > 0
