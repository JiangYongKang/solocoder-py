from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import CredentialVersion, FallbackReason, RotationPhase, WriteSide


@dataclass
class CredentialInfo:
    version: str
    credential_type: CredentialVersion
    data: dict = field(default_factory=dict)
    description: Optional[str] = None


@dataclass
class RotationConfig:
    credential_name: str
    old_credential: str
    new_credential: str
    dual_write_duration_seconds: float = 300.0
    traffic_step_percentage: int = 10
    max_error_rate: float = 0.05
    consecutive_failure_threshold: int = 5
    cooldown_seconds: float = 120.0
    min_requests_for_evaluation: int = 50
    auto_recover_enabled: bool = True
    old_credential_data: dict = field(default_factory=dict)
    new_credential_data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        from .exceptions import InvalidConfigError

        if not self.credential_name:
            raise InvalidConfigError("credential_name must not be empty")
        if not self.old_credential:
            raise InvalidConfigError("old_credential must not be empty")
        if not self.new_credential:
            raise InvalidConfigError("new_credential must not be empty")
        if self.old_credential == self.new_credential:
            raise InvalidConfigError("old_credential and new_credential must be different")
        if self.dual_write_duration_seconds <= 0:
            raise InvalidConfigError("dual_write_duration_seconds must be positive")
        if self.traffic_step_percentage <= 0 or self.traffic_step_percentage > 100:
            raise InvalidConfigError("traffic_step_percentage must be in (0, 100]")
        if self.max_error_rate < 0 or self.max_error_rate > 1:
            raise InvalidConfigError("max_error_rate must be in [0, 1]")
        if self.consecutive_failure_threshold <= 0:
            raise InvalidConfigError("consecutive_failure_threshold must be positive")
        if self.cooldown_seconds <= 0:
            raise InvalidConfigError("cooldown_seconds must be positive")
        if self.min_requests_for_evaluation <= 0:
            raise InvalidConfigError("min_requests_for_evaluation must be positive")


@dataclass
class TrafficStats:
    total_requests: int = 0
    old_requests: int = 0
    new_requests: int = 0
    old_errors: int = 0
    new_errors: int = 0
    new_consecutive_failures: int = 0

    @property
    def old_error_rate(self) -> float:
        if self.old_requests == 0:
            return 0.0
        return self.old_errors / self.old_requests

    @property
    def new_error_rate(self) -> float:
        if self.new_requests == 0:
            return 0.0
        return self.new_errors / self.new_requests


@dataclass
class WriteFailureRecord:
    timestamp: float
    side: WriteSide
    error_message: str


@dataclass
class WriteResult:
    old_attempted: bool
    new_attempted: bool
    old_success: Optional[bool]
    new_success: Optional[bool]
    old_error: Optional[str] = None
    new_error: Optional[str] = None

    @property
    def all_succeeded(self) -> bool:
        if self.old_attempted and self.old_success is not True:
            return False
        if self.new_attempted and self.new_success is not True:
            return False
        return True

    @property
    def any_failed(self) -> bool:
        if self.old_attempted and self.old_success is False:
            return True
        if self.new_attempted and self.new_success is False:
            return True
        return False

    @property
    def any_attempted(self) -> bool:
        return self.old_attempted or self.new_attempted


@dataclass
class FallbackRecord:
    timestamp: float
    reason: FallbackReason
    traffic_percentage_at_fallback: int
    failure_count: int
    detail: str


@dataclass
class RotationState:
    name: str
    config: RotationConfig
    phase: RotationPhase = RotationPhase.IDLE
    current_traffic_percentage: int = 0
    dual_write_started_at: Optional[float] = None
    canary_started_at: Optional[float] = None
    cooldown_started_at: Optional[float] = None
    completed_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    fallback_records: list[FallbackRecord] = field(default_factory=list)
    write_failure_records: list[WriteFailureRecord] = field(default_factory=list)
    traffic_stats: TrafficStats = field(default_factory=TrafficStats)
    max_traffic_reached: int = 0

    @property
    def is_dual_write_active(self) -> bool:
        return self.phase in (RotationPhase.DUAL_WRITE, RotationPhase.CANARY, RotationPhase.COOLDOWN)

    @property
    def is_new_credential_active(self) -> bool:
        return self.phase in (RotationPhase.CANARY, RotationPhase.COOLDOWN, RotationPhase.COMPLETED)

    @property
    def is_rolled_back(self) -> bool:
        return self.phase == RotationPhase.ROLLED_BACK

    @property
    def is_completed(self) -> bool:
        return self.phase == RotationPhase.COMPLETED
