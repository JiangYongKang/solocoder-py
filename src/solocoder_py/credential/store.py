from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from typing import Any, Optional

from .enums import CredentialVersion, FallbackReason, RotationPhase, WriteSide
from .models import (
    CredentialInfo,
    FallbackRecord,
    RotationConfig,
    RotationState,
    TrafficStats,
    WriteFailureRecord,
)


@dataclass
class SerializedState:
    name: str
    config: dict[str, Any]
    phase: str
    current_traffic_percentage: int
    dual_write_started_at: Optional[float]
    canary_started_at: Optional[float]
    cooldown_started_at: Optional[float]
    completed_at: Optional[float]
    rolled_back_at: Optional[float]
    fallback_records: list[dict[str, Any]]
    write_failure_records: list[dict[str, Any]]
    traffic_stats: dict[str, Any]
    max_traffic_reached: int


def _serialize_state(state: RotationState) -> SerializedState:
    return SerializedState(
        name=state.name,
        config={
            "credential_name": state.config.credential_name,
            "old_credential": state.config.old_credential,
            "new_credential": state.config.new_credential,
            "dual_write_duration_seconds": state.config.dual_write_duration_seconds,
            "traffic_step_percentage": state.config.traffic_step_percentage,
            "max_error_rate": state.config.max_error_rate,
            "consecutive_failure_threshold": state.config.consecutive_failure_threshold,
            "cooldown_seconds": state.config.cooldown_seconds,
            "min_requests_for_evaluation": state.config.min_requests_for_evaluation,
            "auto_recover_enabled": state.config.auto_recover_enabled,
            "old_credential_data": state.config.old_credential_data,
            "new_credential_data": state.config.new_credential_data,
        },
        phase=state.phase.value,
        current_traffic_percentage=state.current_traffic_percentage,
        dual_write_started_at=state.dual_write_started_at,
        canary_started_at=state.canary_started_at,
        cooldown_started_at=state.cooldown_started_at,
        completed_at=state.completed_at,
        rolled_back_at=state.rolled_back_at,
        fallback_records=[
            {
                "timestamp": r.timestamp,
                "reason": r.reason.value,
                "traffic_percentage_at_fallback": r.traffic_percentage_at_fallback,
                "failure_count": r.failure_count,
                "detail": r.detail,
            }
            for r in state.fallback_records
        ],
        write_failure_records=[
            {
                "timestamp": r.timestamp,
                "side": r.side.value,
                "error_message": r.error_message,
            }
            for r in state.write_failure_records
        ],
        traffic_stats={
            "total_requests": state.traffic_stats.total_requests,
            "old_requests": state.traffic_stats.old_requests,
            "new_requests": state.traffic_stats.new_requests,
            "old_errors": state.traffic_stats.old_errors,
            "new_errors": state.traffic_stats.new_errors,
            "new_consecutive_failures": state.traffic_stats.new_consecutive_failures,
        },
        max_traffic_reached=state.max_traffic_reached,
    )


def _deserialize_state(data: SerializedState) -> RotationState:
    config = RotationConfig(
        credential_name=data.config["credential_name"],
        old_credential=data.config["old_credential"],
        new_credential=data.config["new_credential"],
        dual_write_duration_seconds=data.config["dual_write_duration_seconds"],
        traffic_step_percentage=data.config["traffic_step_percentage"],
        max_error_rate=data.config["max_error_rate"],
        consecutive_failure_threshold=data.config["consecutive_failure_threshold"],
        cooldown_seconds=data.config["cooldown_seconds"],
        min_requests_for_evaluation=data.config["min_requests_for_evaluation"],
        auto_recover_enabled=data.config["auto_recover_enabled"],
        old_credential_data=data.config.get("old_credential_data", {}),
        new_credential_data=data.config.get("new_credential_data", {}),
    )

    fallback_records = [
        FallbackRecord(
            timestamp=r["timestamp"],
            reason=FallbackReason(r["reason"]),
            traffic_percentage_at_fallback=r["traffic_percentage_at_fallback"],
            failure_count=r["failure_count"],
            detail=r["detail"],
        )
        for r in data.fallback_records
    ]

    write_failure_records = [
        WriteFailureRecord(
            timestamp=r["timestamp"],
            side=WriteSide(r["side"]),
            error_message=r["error_message"],
        )
        for r in data.write_failure_records
    ]

    stats = data.traffic_stats
    traffic_stats = TrafficStats(
        total_requests=stats["total_requests"],
        old_requests=stats["old_requests"],
        new_requests=stats["new_requests"],
        old_errors=stats["old_errors"],
        new_errors=stats["new_errors"],
        new_consecutive_failures=stats["new_consecutive_failures"],
    )

    return RotationState(
        name=data.name,
        config=config,
        phase=RotationPhase(data.phase),
        current_traffic_percentage=data.current_traffic_percentage,
        dual_write_started_at=data.dual_write_started_at,
        canary_started_at=data.canary_started_at,
        cooldown_started_at=data.cooldown_started_at,
        completed_at=data.completed_at,
        rolled_back_at=data.rolled_back_at,
        fallback_records=fallback_records,
        write_failure_records=write_failure_records,
        traffic_stats=traffic_stats,
        max_traffic_reached=data.max_traffic_reached,
    )


class RotationStore:
    def __init__(self) -> None:
        self._states: dict[str, RotationState] = {}
        self._lock = threading.RLock()

    def save(self, state: RotationState) -> None:
        with self._lock:
            self._states[state.name] = state

    def load(self, name: str) -> Optional[RotationState]:
        with self._lock:
            return self._states.get(name)

    def delete(self, name: str) -> bool:
        with self._lock:
            if name in self._states:
                del self._states[name]
                return True
            return False

    def list_all(self) -> list[RotationState]:
        with self._lock:
            return list(self._states.values())

    def to_json(self, name: str) -> str:
        with self._lock:
            state = self.load(name)
            if state is None:
                raise KeyError(f"rotation '{name}' not found")
            serialized = _serialize_state(state)
            return json.dumps(asdict(serialized), ensure_ascii=False)

    def from_json(self, json_str: str) -> RotationState:
        with self._lock:
            data_dict = json.loads(json_str)
            serialized = SerializedState(**data_dict)
            state = _deserialize_state(serialized)
            self.save(state)
            return state

    def snapshot_all(self) -> dict[str, str]:
        with self._lock:
            result: dict[str, str] = {}
            for name in self._states:
                result[name] = self.to_json(name)
            return result

    def restore_all(self, snapshots: dict[str, str]) -> None:
        with self._lock:
            for json_str in snapshots.values():
                self.from_json(json_str)
