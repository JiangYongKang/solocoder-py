from __future__ import annotations

from enum import Enum


class RotationPhase(Enum):
    IDLE = "IDLE"
    DUAL_WRITE = "DUAL_WRITE"
    CANARY = "CANARY"
    COOLDOWN = "COOLDOWN"
    COMPLETED = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"


class CredentialVersion(Enum):
    OLD = "OLD"
    NEW = "NEW"


class FallbackReason(Enum):
    CONSECUTIVE_FAILURES = "CONSECUTIVE_FAILURES"
    ERROR_RATE_EXCEEDED = "ERROR_RATE_EXCEEDED"
    MANUAL = "MANUAL"


class WriteSide(Enum):
    OLD = "OLD"
    NEW = "NEW"
    BOTH = "BOTH"
