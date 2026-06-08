from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .exceptions import ReplicaInjectedFailureError, ReplicaUnreachableError
from .models import ReplicaStats, ReplicaStatus, StoredValue


@dataclass
class Replica:
    id: str
    name: str = ""
    _status: ReplicaStatus = ReplicaStatus.ONLINE
    _store: dict[str, StoredValue] = field(default_factory=dict)
    _total_reads: int = 0
    _successful_reads: int = 0
    _total_writes: int = 0
    _successful_writes: int = 0
    _read_latencies_ms: list[float] = field(default_factory=list)
    _write_latencies_ms: list[float] = field(default_factory=list)
    _artificial_latency_ms: float = 0.0
    _fail_reads: bool = False
    _fail_writes: bool = False

    @property
    def status(self) -> ReplicaStatus:
        return self._status

    @property
    def artificial_latency_ms(self) -> float:
        return self._artificial_latency_ms

    def mark_unreachable(self) -> None:
        self._status = ReplicaStatus.UNREACHABLE

    def mark_online(self) -> None:
        self._status = ReplicaStatus.ONLINE

    def set_artificial_latency(self, latency_ms: float) -> None:
        self._artificial_latency_ms = max(0.0, latency_ms)

    def set_fail_reads(self, fail: bool) -> None:
        self._fail_reads = fail

    def set_fail_writes(self, fail: bool) -> None:
        self._fail_writes = fail

    def _check_reachable(self) -> None:
        if self._status == ReplicaStatus.UNREACHABLE:
            raise ReplicaUnreachableError(self.id)

    def _sleep_latency(self) -> None:
        if self._artificial_latency_ms > 0:
            time.sleep(self._artificial_latency_ms / 1000.0)

    def read(self, key: str) -> Optional[StoredValue]:
        self._total_reads += 1
        self._check_reachable()
        if self._fail_reads:
            raise ReplicaInjectedFailureError(self.id, "read")
        self._sleep_latency()
        start = time.monotonic()
        value = self._store.get(key)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        self._read_latencies_ms.append(elapsed_ms)
        self._successful_reads += 1
        return value

    def write(self, key: str, value: Any, version: int) -> bool:
        self._total_writes += 1
        self._check_reachable()
        if self._fail_writes:
            raise ReplicaInjectedFailureError(self.id, "write")
        self._sleep_latency()
        start = time.monotonic()
        existing = self._store.get(key)
        if existing is not None and version < existing.version:
            return False
        timestamp = time.time()
        self._store[key] = StoredValue(value=value, version=version, timestamp=timestamp)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        self._write_latencies_ms.append(elapsed_ms)
        self._successful_writes += 1
        return True

    def get_all_data(self) -> dict[str, StoredValue]:
        return dict(self._store)

    def get_version(self, key: str) -> int:
        stored = self._store.get(key)
        if stored is None:
            return 0
        return stored.version

    def get_stats(self) -> ReplicaStats:
        return ReplicaStats(
            replica_id=self.id,
            status=self._status,
            keys_count=len(self._store),
            total_reads=self._total_reads,
            successful_reads=self._successful_reads,
            total_writes=self._total_writes,
            successful_writes=self._successful_writes,
            read_latencies_ms=list(self._read_latencies_ms),
            write_latencies_ms=list(self._write_latencies_ms),
        )

    def reset_stats(self) -> None:
        self._total_reads = 0
        self._successful_reads = 0
        self._total_writes = 0
        self._successful_writes = 0
        self._read_latencies_ms.clear()
        self._write_latencies_ms.clear()
