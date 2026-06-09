from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from .clock import Clock, SystemClock
from .enums import EntityStatus
from .exceptions import (
    EntityAlreadyRegisteredError,
    EntityNotFoundError,
)
from .models import (
    EntityConfig,
    MonitoredEntity,
    WatchdogConfig,
)


class HeartbeatWatchdog:
    def __init__(
        self,
        config: Optional[WatchdogConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config = config or WatchdogConfig()
        self._clock = clock or SystemClock()
        self._entities: Dict[str, MonitoredEntity] = {}
        self._lock = threading.RLock()

    @property
    def config(self) -> WatchdogConfig:
        return self._config

    def register_entity(
        self,
        entity_id: str,
        lease_ttl: Optional[float] = None,
        debounce_count: Optional[int] = None,
        on_inactive: Optional[Callable[[str], None]] = None,
    ) -> None:
        ttl = lease_ttl if lease_ttl is not None else self._config.default_lease_ttl
        debounce = (
            debounce_count
            if debounce_count is not None
            else self._config.default_debounce_count
        )
        entity_config = EntityConfig(
            entity_id=entity_id,
            lease_ttl=ttl,
            debounce_count=debounce,
            on_inactive=on_inactive,
        )
        self._register_from_config(entity_config)

    def register_entity_from_config(self, config: EntityConfig) -> None:
        self._register_from_config(config)

    def _register_from_config(self, config: EntityConfig) -> None:
        with self._lock:
            if config.entity_id in self._entities:
                raise EntityAlreadyRegisteredError(
                    f"Entity '{config.entity_id}' is already registered"
                )
            now = self._clock.now()
            entity = MonitoredEntity(
                entity_id=config.entity_id,
                lease_ttl=config.lease_ttl,
                debounce_count=config.debounce_count,
                status=EntityStatus.ACTIVE,
                last_heartbeat_at=now,
                inactive_streak=0,
                on_inactive=config.on_inactive,
                status_changed_at=now,
            )
            self._entities[config.entity_id] = entity

    def unregister_entity(self, entity_id: str) -> None:
        with self._lock:
            if entity_id not in self._entities:
                raise EntityNotFoundError(
                    f"Entity '{entity_id}' is not registered"
                )
            del self._entities[entity_id]

    def heartbeat(self, entity_id: str) -> None:
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                raise EntityNotFoundError(
                    f"Entity '{entity_id}' is not registered"
                )
            now = self._clock.now()
            was_inactive = entity.status == EntityStatus.INACTIVE
            entity.record_heartbeat(now)
            if was_inactive:
                entity.transition_to_active(now)

    def get_entity(self, entity_id: str) -> Optional[MonitoredEntity]:
        with self._lock:
            entity = self._entities.get(entity_id)
            return entity.clone() if entity is not None else None

    def get_all_entities(self) -> Dict[str, MonitoredEntity]:
        with self._lock:
            return {eid: ent.clone() for eid, ent in self._entities.items()}

    def get_active_entities(self) -> Dict[str, MonitoredEntity]:
        with self._lock:
            return {
                eid: ent.clone()
                for eid, ent in self._entities.items()
                if ent.status == EntityStatus.ACTIVE
            }

    def get_inactive_entities(self) -> Dict[str, MonitoredEntity]:
        with self._lock:
            return {
                eid: ent.clone()
                for eid, ent in self._entities.items()
                if ent.status == EntityStatus.INACTIVE
            }

    def is_registered(self, entity_id: str) -> bool:
        with self._lock:
            return entity_id in self._entities

    def check_expired(self) -> List[str]:
        with self._lock:
            now = self._clock.now()
            newly_inactive: List[str] = []

            for entity in self._entities.values():
                if entity.status != EntityStatus.ACTIVE:
                    continue

                if entity.is_lease_expired(now):
                    entity.mark_inactive_streak()
                    if entity.should_debounce_to_inactive():
                        entity.transition_to_inactive(now)
                        newly_inactive.append(entity.entity_id)
                        if entity.on_inactive is not None:
                            try:
                                entity.on_inactive(entity.entity_id)
                            except Exception:
                                pass

            return newly_inactive

    def check_all(self) -> Dict[str, EntityStatus]:
        with self._lock:
            self.check_expired()
            return {eid: ent.status for eid, ent in self._entities.items()}
