from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .enums import HealthStatus, ProbeType
from .exceptions import InvalidComponentConfigError


CheckResult = Tuple[bool, Optional[str]]
CheckCallable = Callable[[], CheckResult]


@dataclass
class ComponentConfig:
    component_id: str
    is_core: bool = False
    dependencies: List[str] = field(default_factory=list)
    readiness_check: Optional[CheckCallable] = None
    liveness_check: Optional[CheckCallable] = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.component_id or not self.component_id.strip():
            raise InvalidComponentConfigError("component_id must not be empty")
        if self.readiness_check is None and self.liveness_check is None:
            raise InvalidComponentConfigError(
                "At least one of readiness_check or liveness_check must be provided"
            )


@dataclass
class ProbeResult:
    probe_type: ProbeType
    healthy: bool
    error: Optional[str] = None
    cascaded_from: Optional[str] = None


@dataclass
class ComponentHealth:
    component_id: str
    is_core: bool
    readiness: ProbeResult
    liveness: ProbeResult
    dependencies: List[str] = field(default_factory=list)

    def is_ready(self) -> bool:
        return self.readiness.healthy

    def is_alive(self) -> bool:
        return self.liveness.healthy


@dataclass
class DegradedComponent:
    component_id: str
    reason: str


@dataclass
class AggregatedHealth:
    overall_status: HealthStatus
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    degraded_components: List[DegradedComponent] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "overall_status": self.overall_status.value,
            "components": {
                cid: {
                    "is_core": ch.is_core,
                    "readiness": {
                        "healthy": ch.readiness.healthy,
                        "error": ch.readiness.error,
                        "cascaded_from": ch.readiness.cascaded_from,
                    },
                    "liveness": {
                        "healthy": ch.liveness.healthy,
                        "error": ch.liveness.error,
                        "cascaded_from": ch.liveness.cascaded_from,
                    },
                    "dependencies": ch.dependencies,
                }
                for cid, ch in self.components.items()
            },
            "degraded_components": [
                {"component_id": dc.component_id, "reason": dc.reason}
                for dc in self.degraded_components
            ],
        }
