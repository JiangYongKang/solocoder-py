from __future__ import annotations

from enum import Enum


class CanaryPhase(Enum):
    DRAFT = "DRAFT"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"


class RollbackReason(Enum):
    MANUAL = "MANUAL"
    ERROR_RATE_EXCEEDED = "ERROR_RATE_EXCEEDED"
    LATENCY_EXCEEDED = "LATENCY_EXCEEDED"
    METRICS_THRESHOLD_BREACHED = "METRICS_THRESHOLD_BREACHED"


class VersionType(Enum):
    BASELINE = "BASELINE"
    CANDIDATE = "CANDIDATE"
