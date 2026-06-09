from __future__ import annotations

import random
import threading
from typing import Dict, List, Optional

from .clock import Clock, SystemClock
from .exceptions import (
    InstanceAlreadyRegisteredError,
    InstanceNotFoundError,
    ServiceNotFoundError,
)
from .models import RegistryConfig, ServiceInstance, ServiceRegistrySnapshot


class ServiceRegistry:
    def __init__(
        self,
        config: Optional[RegistryConfig] = None,
        clock: Optional[Clock] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._config: RegistryConfig = config or RegistryConfig()
        self._clock: Clock = clock or SystemClock()
        self._rng: random.Random = rng or random.Random()
        self._lock = threading.RLock()
        self._services: Dict[str, ServiceRegistrySnapshot] = {}

    @property
    def config(self) -> RegistryConfig:
        return self._config

    def _evict_expired(self) -> Dict[str, List[str]]:
        now = self._clock.now()
        removed: Dict[str, List[str]] = {}

        for service_name in list(self._services.keys()):
            snapshot = self._services[service_name]
            expired_ids: List[str] = []

            for instance_id, instance in list(snapshot.instances.items()):
                if instance.is_expired(now, self._config.default_ttl):
                    expired_ids.append(instance_id)
                    del snapshot.instances[instance_id]

            if expired_ids:
                removed[service_name] = expired_ids

            if not snapshot.instances:
                del self._services[service_name]

        return removed

    def register(self, instance: ServiceInstance) -> ServiceInstance:
        with self._lock:
            self._evict_expired()
            now = self._clock.now()
            service_name = instance.service_name

            if service_name not in self._services:
                self._services[service_name] = ServiceRegistrySnapshot(service_name=service_name)

            snapshot = self._services[service_name]
            if instance.instance_id in snapshot.instances:
                raise InstanceAlreadyRegisteredError(
                    f"Instance '{instance.instance_id}' is already registered for service '{service_name}'"
                )

            new_instance = instance.clone()
            new_instance.registered_at = now
            new_instance.last_heartbeat = now
            snapshot.instances[instance.instance_id] = new_instance
            return new_instance.clone()

    def renew(self, service_name: str, instance_id: str) -> ServiceInstance:
        with self._lock:
            self._evict_expired()
            now = self._clock.now()
            self._ensure_service_exists(service_name)

            snapshot = self._services[service_name]
            instance = snapshot.instances.get(instance_id)
            if instance is None:
                raise InstanceNotFoundError(
                    f"Instance '{instance_id}' not found for service '{service_name}'"
                )

            instance.last_heartbeat = now
            return instance.clone()

    def deregister(self, service_name: str, instance_id: str) -> bool:
        with self._lock:
            self._evict_expired()
            self._ensure_service_exists(service_name)

            snapshot = self._services[service_name]
            if instance_id not in snapshot.instances:
                raise InstanceNotFoundError(
                    f"Instance '{instance_id}' not found for service '{service_name}'"
                )

            del snapshot.instances[instance_id]

            if not snapshot.instances:
                del self._services[service_name]

            return True

    def get_instances(self, service_name: str) -> List[ServiceInstance]:
        with self._lock:
            self._evict_expired()
            self._ensure_service_exists(service_name)

            snapshot = self._services[service_name]
            return [v.clone() for v in snapshot.instances.values() if v.weight > 0]

    def get_all_instances(self, service_name: str) -> List[ServiceInstance]:
        with self._lock:
            self._evict_expired()
            self._ensure_service_exists(service_name)
            snapshot = self._services[service_name]
            return [v.clone() for v in snapshot.instances.values()]

    def select_instance(self, service_name: str) -> ServiceInstance:
        with self._lock:
            self._evict_expired()
            self._ensure_service_exists(service_name)

            snapshot = self._services[service_name]
            all_candidates = list(snapshot.instances.values())
            positive_weight_candidates = [inst for inst in all_candidates if inst.weight > 0]

            if positive_weight_candidates:
                candidates = positive_weight_candidates
            else:
                candidates = all_candidates

            total_weight = sum(inst.weight for inst in candidates)

            if total_weight <= 0:
                return self._rng.choice(candidates).clone()

            pick = self._rng.uniform(0, total_weight)
            cumulative = 0.0
            for inst in candidates:
                cumulative += inst.weight
                if pick < cumulative:
                    return inst.clone()

            return candidates[-1].clone()

    def cleanup_expired(self) -> Dict[str, List[str]]:
        with self._lock:
            return self._evict_expired()

    def list_services(self) -> List[str]:
        with self._lock:
            self._evict_expired()
            return list(self._services.keys())

    def service_count(self) -> int:
        with self._lock:
            self._evict_expired()
            return len(self._services)

    def instance_count(self, service_name: Optional[str] = None) -> int:
        with self._lock:
            self._evict_expired()
            if service_name is None:
                return sum(len(s.instances) for s in self._services.values())
            self._ensure_service_exists(service_name)
            return len(self._services[service_name].instances)

    def _ensure_service_exists(self, service_name: str) -> None:
        if service_name not in self._services:
            raise ServiceNotFoundError(f"Service '{service_name}' not found")
