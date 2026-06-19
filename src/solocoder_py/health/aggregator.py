from __future__ import annotations

import threading
from typing import Dict, List, Optional, Set

from .enums import HealthStatus, ProbeType
from .exceptions import (
    CircularDependencyError,
    ComponentAlreadyRegisteredError,
    ComponentNotFoundError,
    InvalidComponentConfigError,
)
from .models import (
    AggregatedHealth,
    CheckResult,
    ComponentConfig,
    ComponentHealth,
    DegradedComponent,
    ProbeResult,
)


class HealthCheckAggregator:
    def __init__(self) -> None:
        self._components: Dict[str, ComponentConfig] = {}
        self._lock = threading.RLock()

    def register_component(self, config: ComponentConfig) -> None:
        with self._lock:
            if config.component_id in self._components:
                raise ComponentAlreadyRegisteredError(
                    f"Component '{config.component_id}' is already registered"
                )
            for dep in config.dependencies:
                if dep == config.component_id:
                    raise CircularDependencyError(
                        f"Component '{config.component_id}' cannot depend on itself"
                    )
                if dep not in self._components:
                    raise ComponentNotFoundError(
                        f"Dependency '{dep}' for component '{config.component_id}' is not registered"
                    )
            self._components[config.component_id] = config
            try:
                self._detect_circular_dependencies()
            except CircularDependencyError:
                del self._components[config.component_id]
                raise

    def unregister_component(self, component_id: str) -> None:
        with self._lock:
            if component_id not in self._components:
                raise ComponentNotFoundError(
                    f"Component '{component_id}' is not registered"
                )
            for cid, cfg in self._components.items():
                if cid != component_id and component_id in cfg.dependencies:
                    raise InvalidComponentConfigError(
                        f"Cannot unregister '{component_id}': it is a dependency of '{cid}'"
                    )
            del self._components[component_id]

    def is_registered(self, component_id: str) -> bool:
        with self._lock:
            return component_id in self._components

    def get_component_config(self, component_id: str) -> Optional[ComponentConfig]:
        with self._lock:
            cfg = self._components.get(component_id)
            if cfg is None:
                return None
            return ComponentConfig(
                component_id=cfg.component_id,
                is_core=cfg.is_core,
                dependencies=list(cfg.dependencies),
                readiness_check=cfg.readiness_check,
                liveness_check=cfg.liveness_check,
            )

    def get_all_component_ids(self) -> List[str]:
        with self._lock:
            return list(self._components.keys())

    def check_component(self, component_id: str) -> ComponentHealth:
        with self._lock:
            if component_id not in self._components:
                raise ComponentNotFoundError(
                    f"Component '{component_id}' is not registered"
                )
            return self._check_component_internal(component_id, set())

    def check_all(self) -> AggregatedHealth:
        with self._lock:
            return self._check_all_internal()

    def _check_all_internal(self) -> AggregatedHealth:
        component_healths: Dict[str, ComponentHealth] = {}
        checking: Set[str] = set()

        for cid in self._components:
            if cid not in component_healths:
                self._check_component_with_cache(cid, checking, component_healths)

        degraded: List[DegradedComponent] = []
        has_unavailable_core = False

        for cid, health in component_healths.items():
            if not health.is_alive() and health.is_core:
                has_unavailable_core = True
            elif not health.is_alive():
                reason = health.liveness.error or "Liveness probe failed"
                degraded.append(
                    DegradedComponent(component_id=cid, reason=reason)
                )
            elif not health.is_ready():
                reason = health.readiness.error or "Readiness probe failed"
                if health.readiness.root_cause:
                    reason = f"Cascaded from unhealthy dependency: {health.readiness.root_cause}"
                elif health.readiness.cascaded_from:
                    reason = f"Cascaded from unhealthy dependency: {health.readiness.cascaded_from}"
                degraded.append(
                    DegradedComponent(component_id=cid, reason=reason)
                )

        if has_unavailable_core:
            overall = HealthStatus.UNAVAILABLE
        elif degraded:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return AggregatedHealth(
            overall_status=overall,
            components=component_healths,
            degraded_components=degraded,
        )

    def _check_component_internal(
        self, component_id: str, checking: Set[str]
    ) -> ComponentHealth:
        cache: Dict[str, ComponentHealth] = {}
        return self._check_component_with_cache(component_id, checking, cache)

    def _check_component_with_cache(
        self,
        component_id: str,
        checking: Set[str],
        cache: Dict[str, ComponentHealth],
    ) -> ComponentHealth:
        if component_id in cache:
            return cache[component_id]
        if component_id in checking:
            raise CircularDependencyError(
                f"Circular dependency detected involving '{component_id}'"
            )

        config = self._components[component_id]
        checking.add(component_id)

        try:
            readiness_result = self._run_probe(
                ProbeType.READINESS, config.readiness_check
            )
            liveness_result = self._run_probe(
                ProbeType.LIVENESS, config.liveness_check
            )

            for dep in config.dependencies:
                dep_health = self._check_component_with_cache(
                    dep, checking, cache
                )
                if readiness_result.healthy and not dep_health.is_ready():
                    root_cause = dep_health.readiness.root_cause or dep
                    readiness_result = ProbeResult(
                        probe_type=ProbeType.READINESS,
                        healthy=False,
                        error=f"Dependency '{dep}' is not ready",
                        cascaded_from=dep,
                        root_cause=root_cause,
                    )

            health = ComponentHealth(
                component_id=component_id,
                is_core=config.is_core,
                readiness=readiness_result,
                liveness=liveness_result,
                dependencies=list(config.dependencies),
            )
            cache[component_id] = health
            return health
        finally:
            checking.discard(component_id)

    def _run_probe(
        self, probe_type: ProbeType, check_func
    ) -> ProbeResult:
        if check_func is None:
            return ProbeResult(
                probe_type=probe_type,
                healthy=True,
                error=None,
            )
        try:
            result = check_func()
            if isinstance(result, tuple):
                healthy, error = result
                if error is not None and not isinstance(error, str):
                    error = str(error)
            else:
                healthy = bool(result)
                error = None
            return ProbeResult(
                probe_type=probe_type,
                healthy=healthy,
                error=error,
            )
        except Exception as e:
            return ProbeResult(
                probe_type=probe_type,
                healthy=False,
                error=f"Check function raised exception: {type(e).__name__}: {e}",
            )

    def _detect_circular_dependencies(self) -> None:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {cid: WHITE for cid in self._components}

        def dfs(node: str) -> None:
            color[node] = GRAY
            for dep in self._components[node].dependencies:
                if color[dep] == GRAY:
                    raise CircularDependencyError(
                        f"Circular dependency detected: {node} -> {dep}"
                    )
                if color[dep] == WHITE:
                    dfs(dep)
            color[node] = BLACK

        for cid in self._components:
            if color[cid] == WHITE:
                dfs(cid)
