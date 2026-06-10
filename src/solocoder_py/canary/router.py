from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .enums import VersionType
from .exceptions import InvalidTrafficPercentageError, ReleaseNotFoundError, VersionNotFoundError
from .models import TrafficStats, VersionInfo


BUCKET_COUNT = 100


class StableHashBucketer:
    @staticmethod
    def _hash(key: str) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], byteorder="big", signed=False)

    @classmethod
    def get_bucket(cls, request_key: str) -> int:
        return cls._hash(request_key) % BUCKET_COUNT


@dataclass
class _ReleaseRoutingState:
    baseline_version: str
    candidate_version: str
    traffic_percentage: int = 0
    stats: TrafficStats = field(default_factory=TrafficStats)


class TrafficRouter:
    def __init__(self) -> None:
        self._versions: dict[str, VersionInfo] = {}
        self._release_states: dict[str, _ReleaseRoutingState] = {}
        self._lock = threading.RLock()

    def register_release(
        self,
        release_name: str,
        baseline_version: str,
        candidate_version: str,
        baseline_description: Optional[str] = None,
        candidate_description: Optional[str] = None,
    ) -> None:
        if not release_name:
            raise ValueError("release_name must not be empty")
        if not baseline_version:
            raise ValueError("baseline_version must not be empty")
        if not candidate_version:
            raise ValueError("candidate_version must not be empty")
        if baseline_version == candidate_version:
            raise ValueError("baseline and candidate versions must be different")

        with self._lock:
            if baseline_version not in self._versions:
                self._versions[baseline_version] = VersionInfo(
                    version=baseline_version,
                    version_type=VersionType.BASELINE,
                    description=baseline_description,
                )
            if candidate_version not in self._versions:
                self._versions[candidate_version] = VersionInfo(
                    version=candidate_version,
                    version_type=VersionType.CANDIDATE,
                    description=candidate_description,
                )

            self._release_states[release_name] = _ReleaseRoutingState(
                baseline_version=baseline_version,
                candidate_version=candidate_version,
                traffic_percentage=0,
            )

    def set_traffic_percentage(self, release_name: str, percentage: int) -> None:
        if percentage < 0 or percentage > 100:
            raise InvalidTrafficPercentageError("traffic percentage must be between 0 and 100")

        with self._lock:
            self._get_release_state_or_raise(release_name)
            self._release_states[release_name].traffic_percentage = percentage

    def get_traffic_percentage(self, release_name: str) -> int:
        with self._lock:
            state = self._get_release_state_or_raise(release_name)
            return state.traffic_percentage

    def route(self, release_name: str, request_key: str) -> Tuple[str, VersionType]:
        if not release_name:
            raise ValueError("release_name must not be empty")
        if not request_key:
            raise ValueError("request_key must not be empty")

        with self._lock:
            state = self._get_release_state_or_raise(release_name)

            bucket = StableHashBucketer.get_bucket(request_key)

            if bucket < state.traffic_percentage:
                target_version = state.candidate_version
                target_type = VersionType.CANDIDATE
            else:
                target_version = state.baseline_version
                target_type = VersionType.BASELINE

            state.stats.total_requests += 1
            if target_type == VersionType.BASELINE:
                state.stats.baseline_requests += 1
            else:
                state.stats.candidate_requests += 1

            return target_version, target_type

    def record_metrics(
        self,
        release_name: str,
        version_type: VersionType,
        latency_ms: float,
        is_error: bool = False,
    ) -> None:
        if latency_ms < 0:
            raise ValueError("latency_ms must not be negative")

        with self._lock:
            state = self._get_release_state_or_raise(release_name)
            stats = state.stats

            if version_type == VersionType.BASELINE:
                stats.baseline_total_latency_ms += latency_ms
                stats.baseline_latency_samples.append(latency_ms)
                if is_error:
                    stats.baseline_errors += 1
            elif version_type == VersionType.CANDIDATE:
                stats.candidate_total_latency_ms += latency_ms
                stats.candidate_latency_samples.append(latency_ms)
                if is_error:
                    stats.candidate_errors += 1

    def record_candidate_metrics(
        self,
        release_name: str,
        latency_ms: float,
        is_error: bool = False,
    ) -> None:
        self.record_metrics(release_name, VersionType.CANDIDATE, latency_ms, is_error)

    def get_stats(self, release_name: str) -> TrafficStats:
        with self._lock:
            state = self._get_release_state_or_raise(release_name)
            return state.stats

    def reset_stats(self, release_name: str) -> None:
        with self._lock:
            state = self._get_release_state_or_raise(release_name)
            state.stats = TrafficStats()

    def list_versions(self) -> list[VersionInfo]:
        with self._lock:
            return list(self._versions.values())

    def get_version(self, version: str) -> VersionInfo:
        with self._lock:
            if version not in self._versions:
                raise VersionNotFoundError(f"version '{version}' not found")
            return self._versions[version]

    def has_release(self, release_name: str) -> bool:
        with self._lock:
            return release_name in self._release_states

    def _get_release_state_or_raise(self, release_name: str) -> _ReleaseRoutingState:
        if release_name not in self._release_states:
            raise ReleaseNotFoundError(f"release '{release_name}' not found in router")
        return self._release_states[release_name]
