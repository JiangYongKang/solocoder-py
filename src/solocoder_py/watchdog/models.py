from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .enums import EntityStatus
from .exceptions import InvalidConfigError


@dataclass
class WatchdogConfig:
    default_lease_ttl: float = 10.0
    default_debounce_count: int = 3

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.default_lease_ttl <= 0:
            raise InvalidConfigError("default_lease_ttl must be positive")
        if self.default_debounce_count <= 0:
            raise InvalidConfigError("default_debounce_count must be positive")


@dataclass
class EntityConfig:
    entity_id: str
    lease_ttl: float
    debounce_count: int
    on_inactive: Optional[Callable[[str], None]] = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.entity_id:
            raise InvalidConfigError("entity_id must not be empty")
        if self.lease_ttl <= 0:
            raise InvalidConfigError("lease_ttl must be positive")
        if self.debounce_count <= 0:
            raise InvalidConfigError("debounce_count must be positive")


@dataclass
class MonitoredEntity:
    entity_id: str
    lease_ttl: float
    debounce_count: int
    status: EntityStatus = EntityStatus.ACTIVE
    last_heartbeat_at: float = 0.0
    inactive_streak: int = 0
    on_inactive: Optional[Callable[[str], None]] = None
    status_changed_at: float = 0.0

    def record_heartbeat(self, now: float) -> None:
        self.last_heartbeat_at = now
        if self.status == EntityStatus.ACTIVE:
            self.inactive_streak = 0
        else:
            if self.inactive_streak > 0:
                self.inactive_streak = 0

    def is_lease_expired(self, now: float) -> bool:
        return now - self.last_heartbeat_at >= self.lease_ttl

    def mark_inactive_streak(self) -> int:
        self.inactive_streak += 1
        return self.inactive_streak

    def should_debounce_to_inactive(self) -> bool:
        return self.inactive_streak >= self.debounce_count

    def transition_to_inactive(self, now: float) -> None:
        self.status = EntityStatus.INACTIVE
        self.status_changed_at = now

    def transition_to_active(self, now: float) -> None:
        self.status = EntityStatus.ACTIVE
        self.status_changed_at = now
        self.inactive_streak = 0

    def clone(self) -> "MonitoredEntity":
        return MonitoredEntity(
            entity_id=self.entity_id,
            lease_ttl=self.lease_ttl,
            debounce_count=self.debounce_count,
            status=self.status,
            last_heartbeat_at=self.last_heartbeat_at,
            inactive_streak=self.inactive_streak,
            on_inactive=self.on_inactive,
            status_changed_at=self.status_changed_at,
        )
