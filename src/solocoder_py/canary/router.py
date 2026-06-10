from __future__ import annotations

import hashlib
import threading
from typing import Optional, Tuple

from .enums import VersionType
from .exceptions import InvalidTrafficPercentageError, VersionNotFoundError
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


class TrafficRouter:
    def __init__(self) -> None:
        self._versions: dict[str, VersionInfo] = {}
        self._baseline_version: Optional[str] = None
        self._candidate_version: Optional[str] = None
        self._traffic_percentage: int = 0
        self._stats: dict[str, TrafficStats] = {}
        self._lock = threading.RLock()

    def register_version(self, version: str, version_type: VersionType, description: Optional[str] = None) -> VersionInfo:
        if not version:
            raise ValueError("version must not be empty")

        with self._lock:
            info = VersionInfo(version=version, version_type=version_type, description=description)
            self._versions[version] = info

            if version_type == VersionType.BASELINE:
                self._baseline_version = version
            elif version_type == VersionType.CANDIDATE:
                self._candidate_version = version

            return info

    def set_baseline_version(self, version: str) -> None:
        with self._lock:
            if version not in self._versions:
                raise VersionNotFoundError(f"version '{version}' not found")
            self._baseline_version = version

    def set_candidate_version(self, version: str) -> None:
        with self._lock:
            if version not in self._versions:
                raise VersionNotFoundError(f"version '{version}' not found")
            self._candidate_version = version

    def set_traffic_percentage(self, percentage: int) -> None:
        if percentage < 0 or percentage > 100:
            raise InvalidTrafficPercentageError("traffic percentage must be between 0 and 100")

        with self._lock:
            self._traffic_percentage = percentage

    def get_traffic_percentage(self) -> int:
        with self._lock:
            return self._traffic_percentage

    def route(self, request_key: str, release_name: str = "default") -> Tuple[str, VersionType]:
        if not request_key:
            raise ValueError("request_key must not be empty")

        with self._lock:
            if self._baseline_version is None:
                raise VersionNotFoundError("no baseline version registered")
            if self._candidate_version is None:
                raise VersionNotFoundError("no candidate version registered")

            bucket = StableHashBucketer.get_bucket(request_key)

            if bucket < self._traffic_percentage:
                target_version = self._candidate_version
                target_type = VersionType.CANDIDATE
            else:
                target_version = self._baseline_version
                target_type = VersionType.BASELINE

            stats = self._get_or_create_stats(release_name)
            stats.total_requests += 1
            if target_type == VersionType.BASELINE:
                stats.baseline_requests += 1
            else:
                stats.candidate_requests += 1

            return target_version, target_type

    def record_candidate_metrics(
        self,
        release_name: str,
        latency_ms: float,
        is_error: bool = False,
    ) -> None:
        with self._lock:
            stats = self._get_or_create_stats(release_name)
            stats.candidate_total_latency_ms += latency_ms
            stats.candidate_latency_samples.append(latency_ms)
            if is_error:
                stats.candidate_errors += 1

    def get_stats(self, release_name: str) -> TrafficStats:
        with self._lock:
            return self._get_or_create_stats(release_name)

    def reset_stats(self, release_name: str) -> None:
        with self._lock:
            if release_name in self._stats:
                self._stats[release_name] = TrafficStats()

    def list_versions(self) -> list[VersionInfo]:
        with self._lock:
            return list(self._versions.values())

    def get_version(self, version: str) -> VersionInfo:
        with self._lock:
            if version not in self._versions:
                raise VersionNotFoundError(f"version '{version}' not found")
            return self._versions[version]

    def _get_or_create_stats(self, release_name: str) -> TrafficStats:
        if release_name not in self._stats:
            self._stats[release_name] = TrafficStats()
        return self._stats[release_name]
