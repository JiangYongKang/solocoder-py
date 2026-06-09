from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RegistryConfig:
    default_ttl: float = 30.0

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.default_ttl <= 0:
            from .exceptions import InvalidConfigError
            raise InvalidConfigError("default_ttl must be positive")


@dataclass
class ServiceInstance:
    instance_id: str
    service_name: str
    host: str
    port: int
    weight: int = 1
    metadata: Dict[str, str] = field(default_factory=dict)
    registered_at: float = 0.0
    last_heartbeat: float = 0.0

    def __post_init__(self) -> None:
        if self.weight < 0:
            from .exceptions import InvalidConfigError
            raise InvalidConfigError("weight must be non-negative")

    def clone(self) -> "ServiceInstance":
        return ServiceInstance(
            instance_id=self.instance_id,
            service_name=self.service_name,
            host=self.host,
            port=self.port,
            weight=self.weight,
            metadata=dict(self.metadata),
            registered_at=self.registered_at,
            last_heartbeat=self.last_heartbeat,
        )

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def is_expired(self, now: float, ttl: float) -> bool:
        return (now - self.last_heartbeat) >= ttl


@dataclass
class ServiceRegistrySnapshot:
    service_name: str
    instances: Dict[str, ServiceInstance] = field(default_factory=dict)

    def clone(self) -> "ServiceRegistrySnapshot":
        return ServiceRegistrySnapshot(
            service_name=self.service_name,
            instances={k: v.clone() for k, v in self.instances.items()},
        )
