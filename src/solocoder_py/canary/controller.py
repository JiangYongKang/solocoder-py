from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

from .enums import CanaryPhase, RollbackReason, VersionType
from .exceptions import (
    InvalidMetricsThresholdError,
    InvalidReleasePhaseError,
    InvalidTrafficPercentageError,
    ReleaseAlreadyExistsError,
    ReleaseNotFoundError,
    RollbackNotAllowedError,
    VersionNotFoundError,
)
from .models import (
    CanaryRelease,
    CanaryReleaseConfig,
    MetricsSnapshot,
    RollbackRecord,
    TrafficStats,
)
from .router import TrafficRouter


class CanaryController:
    def __init__(self) -> None:
        self._releases: dict[str, CanaryRelease] = {}
        self._router = TrafficRouter()
        self._lock = threading.RLock()

    def create_release(self, name: str, config: CanaryReleaseConfig) -> CanaryRelease:
        if not name:
            raise ValueError("release name must not be empty")

        self._validate_config(config)

        with self._lock:
            if name in self._releases:
                raise ReleaseAlreadyExistsError(f"release '{name}' already exists")

            self._router.register_version(config.baseline_version, VersionType.BASELINE)
            self._router.register_version(config.candidate_version, VersionType.CANDIDATE)

            release = CanaryRelease(
                name=name,
                config=config,
                phase=CanaryPhase.DRAFT,
                created_at=time.time(),
            )
            self._releases[name] = release
            return release

    def start_release(self, name: str) -> CanaryRelease:
        with self._lock:
            release = self._get_release_or_raise(name)

            if release.phase not in (CanaryPhase.DRAFT, CanaryPhase.PAUSED):
                raise InvalidReleasePhaseError(
                    f"cannot start release '{name}' in phase {release.phase.value}"
                )

            release.phase = CanaryPhase.INITIALIZING
            release.started_at = time.time()
            release.current_step_index = -1
            release.current_traffic_percentage = 0
            self._router.set_traffic_percentage(0)

            self._advance_to_next_step(release)
            release.phase = CanaryPhase.RUNNING
            return release

    def pause_release(self, name: str) -> CanaryRelease:
        with self._lock:
            release = self._get_release_or_raise(name)

            if release.phase != CanaryPhase.RUNNING:
                raise InvalidReleasePhaseError(
                    f"cannot pause release '{name}' in phase {release.phase.value}"
                )

            release.phase = CanaryPhase.PAUSED
            return release

    def resume_release(self, name: str) -> CanaryRelease:
        with self._lock:
            release = self._get_release_or_raise(name)

            if release.phase != CanaryPhase.PAUSED:
                raise InvalidReleasePhaseError(
                    f"cannot resume release '{name}' in phase {release.phase.value}"
                )

            release.phase = CanaryPhase.RUNNING
            return release

    def advance_traffic(self, name: str) -> CanaryRelease:
        with self._lock:
            release = self._get_release_or_raise(name)

            if release.phase != CanaryPhase.RUNNING:
                raise InvalidReleasePhaseError(
                    f"cannot advance release '{name}' in phase {release.phase.value}"
                )

            if not release.has_more_steps:
                self._promote_release(release)
                return release

            self._advance_to_next_step(release)
            return release

    def set_traffic_percentage(self, name: str, percentage: int) -> CanaryRelease:
        if percentage < 0 or percentage > 100:
            raise InvalidTrafficPercentageError(
                "traffic percentage must be between 0 and 100"
            )

        with self._lock:
            release = self._get_release_or_raise(name)

            if release.phase not in (CanaryPhase.RUNNING, CanaryPhase.PAUSED):
                raise InvalidReleasePhaseError(
                    f"cannot set traffic for release '{name}' in phase {release.phase.value}"
                )

            release.current_traffic_percentage = percentage
            self._router.set_traffic_percentage(percentage)
            return release

    def rollback(self, name: str, reason: str = "Manual rollback") -> CanaryRelease:
        with self._lock:
            release = self._get_release_or_raise(name)

            if release.phase in (CanaryPhase.ROLLED_BACK, CanaryPhase.PROMOTED, CanaryPhase.DRAFT):
                raise RollbackNotAllowedError(
                    f"cannot rollback release '{name}' in phase {release.phase.value}"
                )

            snapshot = self._take_metrics_snapshot(release)
            self._perform_rollback(release, RollbackReason.MANUAL, reason, snapshot)
            return release

    def evaluate_metrics(self, name: str) -> Tuple[bool, Optional[RollbackRecord]]:
        with self._lock:
            release = self._get_release_or_raise(name)

            if release.phase != CanaryPhase.RUNNING:
                raise InvalidReleasePhaseError(
                    f"cannot evaluate metrics for release '{name}' in phase {release.phase.value}"
                )

            stats = self._router.get_stats(name)
            release.traffic_stats = stats

            snapshot = self._take_metrics_snapshot(release)
            release.metrics_history.append(snapshot)

            if stats.candidate_requests < release.config.min_requests_for_evaluation:
                return True, None

            if stats.candidate_error_rate > release.config.max_error_rate:
                record = self._perform_rollback(
                    release,
                    RollbackReason.ERROR_RATE_EXCEEDED,
                    f"Error rate {stats.candidate_error_rate:.4f} exceeds threshold {release.config.max_error_rate:.4f}",
                    snapshot,
                )
                return False, record

            if stats.candidate_p99_latency_ms > release.config.max_latency_p99_ms:
                record = self._perform_rollback(
                    release,
                    RollbackReason.LATENCY_EXCEEDED,
                    f"P99 latency {stats.candidate_p99_latency_ms:.2f}ms exceeds threshold {release.config.max_latency_p99_ms:.2f}ms",
                    snapshot,
                )
                return False, record

            return True, None

    def route_request(self, release_name: str, request_key: str) -> Tuple[str, VersionType]:
        release = self._get_release_or_raise(release_name)
        if release.phase != CanaryPhase.RUNNING:
            if release.phase == CanaryPhase.ROLLED_BACK:
                return release.config.baseline_version, VersionType.BASELINE
            if release.phase == CanaryPhase.PROMOTED:
                return release.config.candidate_version, VersionType.CANDIDATE
            raise InvalidReleasePhaseError(
                f"cannot route request for release '{release_name}' in phase {release.phase.value}"
            )
        return self._router.route(request_key, release_name)

    def record_request_metrics(
        self,
        release_name: str,
        latency_ms: float,
        is_error: bool = False,
    ) -> None:
        if latency_ms < 0:
            raise ValueError("latency_ms must not be negative")
        self._router.record_candidate_metrics(release_name, latency_ms, is_error)

    def get_release(self, name: str) -> CanaryRelease:
        with self._lock:
            return self._get_release_or_raise(name)

    def list_releases(self) -> list[CanaryRelease]:
        with self._lock:
            return list(self._releases.values())

    def get_traffic_stats(self, name: str) -> TrafficStats:
        self._get_release_or_raise(name)
        return self._router.get_stats(name)

    def get_rollback_history(self, name: str) -> list[RollbackRecord]:
        release = self._get_release_or_raise(name)
        return list(release.rollback_records)

    def reset_release_stats(self, name: str) -> None:
        self._get_release_or_raise(name)
        self._router.reset_stats(name)

    def _validate_config(self, config: CanaryReleaseConfig) -> None:
        if not config.baseline_version:
            raise ValueError("baseline_version must not be empty")
        if not config.candidate_version:
            raise ValueError("candidate_version must not be empty")
        if config.baseline_version == config.candidate_version:
            raise ValueError("baseline and candidate versions must be different")

        if not config.traffic_steps:
            raise InvalidTrafficPercentageError("traffic_steps must not be empty")

        for step in config.traffic_steps:
            if step < 0 or step > 100:
                raise InvalidTrafficPercentageError(
                    f"traffic step {step} must be between 0 and 100"
                )

        for i in range(1, len(config.traffic_steps)):
            if config.traffic_steps[i] <= config.traffic_steps[i - 1]:
                raise InvalidTrafficPercentageError(
                    "traffic_steps must be strictly increasing"
                )

        if config.max_error_rate < 0 or config.max_error_rate > 1:
            raise InvalidMetricsThresholdError(
                "max_error_rate must be between 0 and 1"
            )
        if config.max_latency_p99_ms <= 0:
            raise InvalidMetricsThresholdError(
                "max_latency_p99_ms must be positive"
            )
        if config.min_requests_for_evaluation <= 0:
            raise InvalidMetricsThresholdError(
                "min_requests_for_evaluation must be positive"
            )

    def _advance_to_next_step(self, release: CanaryRelease) -> None:
        release.current_step_index += 1
        next_pct = release.config.traffic_steps[release.current_step_index]
        release.current_traffic_percentage = next_pct
        self._router.set_traffic_percentage(next_pct)

    def _perform_rollback(
        self,
        release: CanaryRelease,
        reason: RollbackReason,
        detail: str,
        snapshot: MetricsSnapshot,
    ) -> RollbackRecord:
        release.phase = CanaryPhase.ROLLED_BACK
        release.rolled_back_at = time.time()
        release.current_traffic_percentage = 0
        self._router.set_traffic_percentage(0)

        record = RollbackRecord(
            timestamp=time.time(),
            reason=reason,
            traffic_percentage_at_rollback=release.current_traffic_percentage,
            detail=detail,
            metrics_snapshot=snapshot,
        )
        release.rollback_records.append(record)
        return record

    def _promote_release(self, release: CanaryRelease) -> None:
        release.phase = CanaryPhase.PROMOTED
        release.promoted_at = time.time()
        release.current_traffic_percentage = 100
        self._router.set_traffic_percentage(100)

    def _take_metrics_snapshot(self, release: CanaryRelease) -> MetricsSnapshot:
        stats = self._router.get_stats(release.name)
        return MetricsSnapshot(
            timestamp=time.time(),
            current_traffic_percentage=release.current_traffic_percentage,
            total_requests=stats.total_requests,
            candidate_requests=stats.candidate_requests,
            candidate_error_rate=stats.candidate_error_rate,
            candidate_p99_latency_ms=stats.candidate_p99_latency_ms,
            candidate_avg_latency_ms=stats.candidate_avg_latency_ms,
        )

    def _get_release_or_raise(self, name: str) -> CanaryRelease:
        if name not in self._releases:
            raise ReleaseNotFoundError(f"release '{name}' not found")
        return self._releases[name]
