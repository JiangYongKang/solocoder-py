from __future__ import annotations

from enum import Enum


class SelectionStrategy(str, Enum):
    ROUND_ROBIN = "ROUND_ROBIN"
    WEIGHTED_RANDOM = "WEIGHTED_RANDOM"
    LEAST_CONNECTIONS = "LEAST_CONNECTIONS"


class InstanceHealth(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"
