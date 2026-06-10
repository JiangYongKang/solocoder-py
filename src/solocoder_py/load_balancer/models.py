from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import CircuitState, InstanceHealth, SelectionStrategy
from .exceptions import InvalidConfigError


@dataclass
class LoadBalancerConfig:
    default_strategy: SelectionStrategy = SelectionStrategy.ROUND_ROBIN
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 30.0
    half_open_max_probes: int = 1

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.failure_threshold <= 0:
            raise InvalidConfigError("failure_threshold must be positive")
        if self.recovery_timeout_seconds <= 0:
            raise InvalidConfigError("recovery_timeout_seconds must be positive")
        if self.half_open_max_probes <= 0:
            raise InvalidConfigError("half_open_max_probes must be positive")


@dataclass
class InstanceConfig:
    instance_id: str
    address: str = ""
    weight: int = 1

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.instance_id:
            raise InvalidConfigError("instance_id must not be empty")
        if self.weight < 0:
            raise InvalidConfigError("weight must be non-negative")


@dataclass
class Instance:
    instance_id: str
    address: str = ""
    weight: int = 1
    health: InstanceHealth = InstanceHealth.HEALTHY
    circuit_state: CircuitState = CircuitState.CLOSED
    active_connections: int = 0
    consecutive_failures: int = 0
    circuit_opened_at: float = 0.0
    half_open_probe_count: int = 0
    allocated_requests: set[int] = field(default_factory=set)

    def is_available(self) -> bool:
        if self.health != InstanceHealth.HEALTHY:
            return False
        if self.circuit_state != CircuitState.CLOSED:
            return False
        if self.weight <= 0:
            return False
        return True

    def is_available_for_half_open(self) -> bool:
        if self.health != InstanceHealth.HEALTHY:
            return False
        if self.circuit_state != CircuitState.HALF_OPEN:
            return False
        if self.weight <= 0:
            return False
        return True

    def mark_healthy(self) -> None:
        self.health = InstanceHealth.HEALTHY

    def mark_unhealthy(self) -> None:
        self.health = InstanceHealth.UNHEALTHY

    def record_success(self) -> None:
        self.consecutive_failures = 0
        if self.circuit_state == CircuitState.HALF_OPEN:
            self.circuit_state = CircuitState.CLOSED
            self.half_open_probe_count = 0

    def record_failure(self, now: float, failure_threshold: int) -> bool:
        self.consecutive_failures += 1
        if self.circuit_state == CircuitState.HALF_OPEN:
            self.circuit_state = CircuitState.OPEN
            self.circuit_opened_at = now
            self.half_open_probe_count = 0
            return True
        if (
            self.circuit_state == CircuitState.CLOSED
            and self.consecutive_failures >= failure_threshold
        ):
            self.circuit_state = CircuitState.OPEN
            self.circuit_opened_at = now
            return True
        return False

    def try_transition_to_half_open(
        self, now: float, recovery_timeout_seconds: float
    ) -> bool:
        if self.circuit_state != CircuitState.OPEN:
            return False
        if now - self.circuit_opened_at >= recovery_timeout_seconds:
            self.circuit_state = CircuitState.HALF_OPEN
            self.half_open_probe_count = 0
            self.consecutive_failures = 0
            return True
        return False

    def acquire_connection(self, request_id: int) -> None:
        self.active_connections += 1
        self.allocated_requests.add(request_id)

    def release_connection(self, request_id: int) -> None:
        if request_id not in self.allocated_requests:
            return False
        self.active_connections -= 1
        self.allocated_requests.remove(request_id)
        return True

    def clone(self) -> "Instance":
        return Instance(
            instance_id=self.instance_id,
            address=self.address,
            weight=self.weight,
            health=self.health,
            circuit_state=self.circuit_state,
            active_connections=self.active_connections,
            consecutive_failures=self.consecutive_failures,
            circuit_opened_at=self.circuit_opened_at,
            half_open_probe_count=self.half_open_probe_count,
            allocated_requests=set(self.allocated_requests),
        )
