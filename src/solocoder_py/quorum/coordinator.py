from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .exceptions import (
    InvalidQuorumConfigError,
    QuorumReadError,
    QuorumWriteError,
    ReplicaUnreachableError,
    VersionConflictError,
)
from .models import (
    ReadResult,
    ReplicaStats,
    ReplicaStatus,
    StoredValue,
    WriteResult,
)
from .replica import Replica


@dataclass
class QuorumCoordinator:
    replicas: list[Replica]
    w: int
    r: int
    _key_versions: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.replicas)
        if n <= 0:
            raise InvalidQuorumConfigError(n, self.w, self.r)
        if self.w <= 0 or self.r <= 0:
            raise InvalidQuorumConfigError(n, self.w, self.r)
        if self.w > n or self.r > n:
            raise InvalidQuorumConfigError(n, self.w, self.r)
        if self.w + self.r <= n:
            raise InvalidQuorumConfigError(n, self.w, self.r)

    @property
    def n(self) -> int:
        return len(self.replicas)

    def _get_next_version(self, key: str) -> int:
        current = self._key_versions.get(key, 0)
        next_version = current + 1
        self._key_versions[key] = next_version
        return next_version

    def write(self, key: str, value: Any, version: Optional[int] = None) -> WriteResult:
        write_version = version if version is not None else self._get_next_version(key)
        successful: list[str] = []
        failed: list[str] = []

        for replica in self.replicas:
            try:
                ok = replica.write(key, value, write_version)
                if ok:
                    successful.append(replica.id)
                else:
                    failed.append(replica.id)
            except ReplicaUnreachableError:
                failed.append(replica.id)

        if len(successful) < self.w:
            raise QuorumWriteError(key, len(successful), self.w)

        stored_version = max(
            [self._key_versions.get(key, 0)]
            + [r.get_version(key) for r in self.replicas if r.id in successful]
        )
        self._key_versions[key] = stored_version

        return WriteResult(
            key=key,
            value=value,
            version=write_version,
            successful_replicas=successful,
            failed_replicas=failed,
        )

    def read(self, key: str, perform_repair: bool = True) -> ReadResult:
        responses: list[tuple[str, Optional[StoredValue]]] = []
        successful: list[str] = []
        failed: list[str] = []

        for replica in self.replicas:
            try:
                value = replica.read(key)
                responses.append((replica.id, value))
                successful.append(replica.id)
            except ReplicaUnreachableError:
                failed.append(replica.id)

        if len(successful) < self.r:
            raise QuorumReadError(key, len(successful), self.r)

        non_none_responses = [(rid, sv) for rid, sv in responses if sv is not None]

        if not non_none_responses:
            return ReadResult(
                key=key,
                value=None,
                version=0,
                successful_replicas=successful,
                failed_replicas=failed,
            )

        versions_set = set(sv.version for _, sv in non_none_responses)
        has_version_conflict = len(versions_set) > 1
        has_missing_data = len(non_none_responses) < len(responses)
        conflict_detected = has_version_conflict

        winning = max(non_none_responses, key=lambda x: (x[1].version, x[1].timestamp))
        winning_replica_id, winning_value = winning

        needs_repair = has_version_conflict or has_missing_data
        repaired: list[str] = []
        if perform_repair and needs_repair:
            repaired = self._repair_replicas(key, winning_value, responses)

        result = ReadResult(
            key=key,
            value=winning_value.value,
            version=winning_value.version,
            successful_replicas=successful,
            failed_replicas=failed,
            repaired_replicas=repaired,
            conflict_detected=conflict_detected,
            winning_value=winning_value,
        )
        return result

    def _repair_replicas(
        self,
        key: str,
        latest: StoredValue,
        responses: list[tuple[str, Optional[StoredValue]]],
    ) -> list[str]:
        repaired: list[str] = []
        for replica_id, stored in responses:
            replica = self._find_replica(replica_id)
            if replica is None:
                continue
            needs_repair = False
            if stored is None:
                needs_repair = True
            elif stored.version < latest.version:
                needs_repair = True
            if needs_repair and replica.status == ReplicaStatus.ONLINE:
                try:
                    ok = replica.write(key, latest.value, latest.version)
                    if ok:
                        repaired.append(replica_id)
                except ReplicaUnreachableError:
                    pass
        return repaired

    def _find_replica(self, replica_id: str) -> Optional[Replica]:
        for r in self.replicas:
            if r.id == replica_id:
                return r
        return None

    def resolve_conflict(
        self,
        key: str,
        raise_on_conflict: bool = False,
    ) -> Optional[StoredValue]:
        responses: list[tuple[str, StoredValue]] = []
        for replica in self.replicas:
            if replica.status == ReplicaStatus.UNREACHABLE:
                continue
            try:
                value = replica.read(key)
                if value is not None:
                    responses.append((replica.id, value))
            except ReplicaUnreachableError:
                continue

        if not responses:
            return None

        versions_list = [(rid, sv.version) for rid, sv in responses]
        versions_set = set(v for _, v in versions_list)
        has_conflict = len(versions_set) > 1

        if has_conflict and raise_on_conflict:
            raise VersionConflictError(key, versions_list)

        winning = max(responses, key=lambda x: (x[1].version, x[1].timestamp))
        winning_value = winning[1]

        for replica_id, _ in responses:
            replica = self._find_replica(replica_id)
            if replica and replica.status == ReplicaStatus.ONLINE:
                try:
                    replica.write(key, winning_value.value, winning_value.version)
                except ReplicaUnreachableError:
                    pass

        return winning_value

    def get_replica(self, replica_id: str) -> Optional[Replica]:
        return self._find_replica(replica_id)

    def get_all_replica_stats(self) -> list[ReplicaStats]:
        return [r.get_stats() for r in self.replicas]

    def get_replica_stats(self, replica_id: str) -> Optional[ReplicaStats]:
        replica = self._find_replica(replica_id)
        if replica is None:
            return None
        return replica.get_stats()

    def mark_replica_unreachable(self, replica_id: str) -> bool:
        replica = self._find_replica(replica_id)
        if replica is None:
            return False
        replica.mark_unreachable()
        return True

    def mark_replica_online(self, replica_id: str) -> bool:
        replica = self._find_replica(replica_id)
        if replica is None:
            return False
        replica.mark_online()
        return True

    def get_all_data_across_replicas(self) -> dict[str, dict[str, StoredValue]]:
        result: dict[str, dict[str, StoredValue]] = {}
        for replica in self.replicas:
            result[replica.id] = replica.get_all_data()
        return result
