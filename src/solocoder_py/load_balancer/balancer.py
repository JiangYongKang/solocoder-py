from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional

from .clock import Clock, SystemClock
from .enums import CircuitState, InstanceHealth, SelectionStrategy
from .exceptions import (
    ConnectionLeakError,
    InstanceAlreadyRegisteredError,
    InstanceNotFoundError,
    NoAvailableInstanceError,
)
from .models import Instance, InstanceConfig, LoadBalancerConfig
from .strategies import (
    LeastConnectionsStrategy,
    RoundRobinStrategy,
    SelectionStrategy as _SelectionStrategy,
    WeightedRandomStrategy,
)


class LoadBalancer:
    def __init__(
        self,
        config: Optional[LoadBalancerConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config: LoadBalancerConfig = config or LoadBalancerConfig()
        self._clock: Clock = clock or SystemClock()
        self._instances: Dict[str, Instance] = {}
        self._current_strategy: SelectionStrategy = self._config.default_strategy
        self._strategies: Dict[SelectionStrategy, _SelectionStrategy] = {
            SelectionStrategy.ROUND_ROBIN: RoundRobinStrategy(),
            SelectionStrategy.WEIGHTED_RANDOM: WeightedRandomStrategy(),
            SelectionStrategy.LEAST_CONNECTIONS: LeastConnectionsStrategy(),
        }
        self._request_counter: int = 0
        self._lock: threading.RLock = threading.RLock()

    @property
    def config(self) -> LoadBalancerConfig:
        return self._config

    @property
    def current_strategy(self) -> SelectionStrategy:
        return self._current_strategy

    def set_strategy(self, strategy: SelectionStrategy) -> None:
        with self._lock:
            self._current_strategy = strategy

    def register_instance(
        self,
        instance_id: str,
        address: str = "",
        weight: int = 1,
    ) -> None:
        cfg = InstanceConfig(
            instance_id=instance_id,
            address=address,
            weight=weight,
        )
        self.register_instance_from_config(cfg)

    def register_instance_from_config(self, config: InstanceConfig) -> None:
        with self._lock:
            if config.instance_id in self._instances:
                raise InstanceAlreadyRegisteredError(
                    f"Instance '{config.instance_id}' is already registered"
                )
            self._instances[config.instance_id] = Instance(
                instance_id=config.instance_id,
                address=config.address,
                weight=config.weight,
            )

    def unregister_instance(self, instance_id: str) -> None:
        with self._lock:
            if instance_id not in self._instances:
                raise InstanceNotFoundError(
                    f"Instance '{instance_id}' is not registered"
                )
            del self._instances[instance_id]

    def mark_healthy(self, instance_id: str) -> None:
        with self._lock:
            instance = self._get_instance_or_raise(instance_id)
            instance.mark_healthy()

    def mark_unhealthy(self, instance_id: str) -> None:
        with self._lock:
            instance = self._get_instance_or_raise(instance_id)
            instance.mark_unhealthy()

    def get_instance(self, instance_id: str) -> Optional[Instance]:
        with self._lock:
            instance = self._instances.get(instance_id)
            return instance.clone() if instance is not None else None

    def get_all_instances(self) -> Dict[str, Instance]:
        with self._lock:
            return {iid: inst.clone() for iid, inst in self._instances.items()}

    def get_available_instances(self) -> Dict[str, Instance]:
        with self._lock:
            self._refresh_circuit_states()
            return {
                iid: inst.clone()
                for iid, inst in self._instances.items()
                if inst.is_available()
            }

    def is_registered(self, instance_id: str) -> bool:
        with self._lock:
            return instance_id in self._instances

    def acquire(
        self,
        strategy: Optional[SelectionStrategy] = None,
    ) -> "Lease":
        with self._lock:
            self._refresh_circuit_states()
            effective_strategy = strategy or self._current_strategy
            available = [
                inst for inst in self._instances.values() if inst.is_available()
            ]
            half_open = [
                inst for inst in self._instances.values()
                if inst.is_available_for_half_open()
                and inst.half_open_probe_count < self._config.half_open_max_probes
            ]

            selected: Optional[Instance] = None
            if half_open:
                selected = half_open[0]
                selected.half_open_probe_count += 1
            elif available:
                strategy_impl = self._strategies[effective_strategy]
                selected = strategy_impl.select(available)

            if selected is None:
                raise NoAvailableInstanceError(
                    "No available instance to handle the request"
                )

            self._request_counter += 1
            request_id = self._request_counter
            selected.acquire_connection(request_id)

            return Lease(
                load_balancer=self,
                instance_id=selected.instance_id,
                request_id=request_id,
            )

    def _release(
        self,
        instance_id: str,
        request_id: int,
        success: bool,
    ) -> None:
        with self._lock:
            instance = self._get_instance_or_raise(instance_id)
            released = instance.release_connection(request_id)
            if not released:
                raise ConnectionLeakError(
                    f"Request {request_id} was not allocated to instance '{instance_id}'"
                )
            now = self._clock.now()
            if success:
                instance.record_success()
            else:
                instance.record_failure(
                    now=now,
                    failure_threshold=self._config.failure_threshold,
                )

    def _get_instance_or_raise(self, instance_id: str) -> Instance:
        instance = self._instances.get(instance_id)
        if instance is None:
            raise InstanceNotFoundError(
                f"Instance '{instance_id}' is not registered"
            )
        return instance

    def _refresh_circuit_states(self) -> None:
        now = self._clock.now()
        for instance in self._instances.values():
            instance.try_transition_to_half_open(
                now=now,
                recovery_timeout_seconds=self._config.recovery_timeout_seconds,
            )


class Lease:
    def __init__(
        self,
        load_balancer: LoadBalancer,
        instance_id: str,
        request_id: int,
    ) -> None:
        self._lb = load_balancer
        self._instance_id = instance_id
        self._request_id = request_id
        self._released: bool = False

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @property
    def request_id(self) -> int:
        return self._request_id

    def release(self, success: bool = True) -> None:
        if self._released:
            raise ConnectionLeakError(
                f"Lease for request {self._request_id} on instance '{self._instance_id}' has already been released"
            )
        self._lb._release(
            instance_id=self._instance_id,
            request_id=self._request_id,
            success=success,
        )
        self._released = True

    def __enter__(self) -> "Lease":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._released:
            return
        success = exc_type is None
        self.release(success=success)
