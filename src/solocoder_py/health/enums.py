from __future__ import annotations

from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ProbeType(str, Enum):
    READINESS = "readiness"
    LIVENESS = "liveness"
