from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import CanaryPhase, RollbackReason, VersionType


@dataclass
class VersionInfo:
    version: str
    version_type: VersionType
    description: Optional[str] = None


@dataclass
class CanaryReleaseConfig:
    baseline_version: str
    candidate_version: str
    traffic_steps: list[int] = field(default_factory=lambda: [1, 5, 20, 50, 100])
    max_error_rate: float = 0.05
    max_latency_p99_ms: float = 500.0
    min_requests_for_evaluation: int = 100
    description: Optional[str] = None


@dataclass
class TrafficStats:
    total_requests: int = 0
    baseline_requests: int = 0
    candidate_requests: int = 0
    baseline_errors: int = 0
    candidate_errors: int = 0
    baseline_total_latency_ms: float = 0.0
    candidate_total_latency_ms: float = 0.0
    baseline_latency_samples: list[float] = field(default_factory=list)
    candidate_latency_samples: list[float] = field(default_factory=list)

    @property
    def baseline_error_rate(self) -> float:
        if self.baseline_requests == 0:
            return 0.0
        return self.baseline_errors / self.baseline_requests

    @property
    def candidate_error_rate(self) -> float:
        if self.candidate_requests == 0:
            return 0.0
        return self.candidate_errors / self.candidate_requests

    @property
    def baseline_avg_latency_ms(self) -> float:
        if self.baseline_requests == 0:
            return 0.0
        return self.baseline_total_latency_ms / self.baseline_requests

    @property
    def candidate_avg_latency_ms(self) -> float:
        if self.candidate_requests == 0:
            return 0.0
        return self.candidate_total_latency_ms / self.candidate_requests

    @staticmethod
    def _p99(samples: list[float]) -> float:
        if not samples:
            return 0.0
        sorted_samples = sorted(samples)
        p99_index = int(len(sorted_samples) * 0.99)
        if p99_index >= len(sorted_samples):
            p99_index = len(sorted_samples) - 1
        return sorted_samples[p99_index]

    @property
    def baseline_p99_latency_ms(self) -> float:
        return self._p99(self.baseline_latency_samples)

    @property
    def candidate_p99_latency_ms(self) -> float:
        return self._p99(self.candidate_latency_samples)


@dataclass
class MetricsSnapshot:
    timestamp: float
    current_traffic_percentage: int
    total_requests: int
    candidate_requests: int
    candidate_error_rate: float
    candidate_p99_latency_ms: float
    candidate_avg_latency_ms: float


@dataclass
class RollbackRecord:
    timestamp: float
    reason: RollbackReason
    traffic_percentage_at_rollback: int
    detail: str
    metrics_snapshot: Optional[MetricsSnapshot] = None


@dataclass
class CanaryRelease:
    name: str
    config: CanaryReleaseConfig
    phase: CanaryPhase = CanaryPhase.DRAFT
    current_step_index: int = -1
    current_traffic_percentage: int = 0
    created_at: float = 0.0
    started_at: Optional[float] = None
    promoted_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    rollback_records: list[RollbackRecord] = field(default_factory=list)
    metrics_history: list[MetricsSnapshot] = field(default_factory=list)
    traffic_stats: TrafficStats = field(default_factory=TrafficStats)

    @property
    def is_running(self) -> bool:
        return self.phase == CanaryPhase.RUNNING

    @property
    def is_rolled_back(self) -> bool:
        return self.phase == CanaryPhase.ROLLED_BACK

    @property
    def is_promoted(self) -> bool:
        return self.phase == CanaryPhase.PROMOTED

    @property
    def has_more_steps(self) -> bool:
        return self.current_step_index < len(self.config.traffic_steps) - 1

    @property
    def next_traffic_percentage(self) -> Optional[int]:
        if not self.has_more_steps:
            return None
        return self.config.traffic_steps[self.current_step_index + 1]
