from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from .clock import Clock, RealClock
from .enums import CredentialVersion, FallbackReason, RotationPhase, WriteSide
from .exceptions import (
    InvalidRotationPhaseError,
    InvalidTrafficPercentageError,
    RotationAlreadyExistsError,
    RotationNotFoundError,
)
from .models import (
    FallbackRecord,
    RotationConfig,
    RotationState,
    TrafficStats,
    WriteFailureRecord,
    WriteResult,
)
from .router import TrafficRouter
from .store import RotationStore


class WriteTarget(ABC):
    @abstractmethod
    def write_old(self, credential: str, data: dict) -> None:
        ...

    @abstractmethod
    def write_new(self, credential: str, data: dict) -> None:
        ...


class MemoryWriteTarget(WriteTarget):
    def __init__(self) -> None:
        self._old_writes: list[Tuple[str, dict]] = []
        self._new_writes: list[Tuple[str, dict]] = []
        self._old_should_fail: bool = False
        self._new_should_fail: bool = False
        self._old_fail_count: int = 0
        self._new_fail_count: int = 0
        self._old_fail_next_n: int = 0
        self._new_fail_next_n: int = 0

    def write_old(self, credential: str, data: dict) -> None:
        if self._old_should_fail or self._old_fail_next_n > 0:
            if self._old_fail_next_n > 0:
                self._old_fail_next_n -= 1
            self._old_fail_count += 1
            raise RuntimeError(f"old system write failure for credential {credential}")
        self._old_writes.append((credential, dict(data)))

    def write_new(self, credential: str, data: dict) -> None:
        if self._new_should_fail or self._new_fail_next_n > 0:
            if self._new_fail_next_n > 0:
                self._new_fail_next_n -= 1
            self._new_fail_count += 1
            raise RuntimeError(f"new system write failure for credential {credential}")
        self._new_writes.append((credential, dict(data)))

    def set_old_should_fail(self, fail: bool) -> None:
        self._old_should_fail = fail

    def set_new_should_fail(self, fail: bool) -> None:
        self._new_should_fail = fail

    def fail_old_next_n(self, n: int) -> None:
        self._old_fail_next_n = n

    def fail_new_next_n(self, n: int) -> None:
        self._new_fail_next_n = n

    def get_old_writes(self) -> list[Tuple[str, dict]]:
        return list(self._old_writes)

    def get_new_writes(self) -> list[Tuple[str, dict]]:
        return list(self._new_writes)

    def get_old_fail_count(self) -> int:
        return self._old_fail_count

    def get_new_fail_count(self) -> int:
        return self._new_fail_count

    def clear(self) -> None:
        self._old_writes.clear()
        self._new_writes.clear()
        self._old_fail_count = 0
        self._new_fail_count = 0


class CredentialRotator:
    def __init__(
        self,
        write_target: Optional[WriteTarget] = None,
        clock: Optional[Clock] = None,
        store: Optional[RotationStore] = None,
        router: Optional[TrafficRouter] = None,
    ) -> None:
        self._write_target = write_target or MemoryWriteTarget()
        self._clock = clock or RealClock()
        self._store = store or RotationStore()
        self._router = router or TrafficRouter()
        self._lock = threading.RLock()

    @property
    def write_target(self) -> WriteTarget:
        return self._write_target

    @property
    def clock(self) -> Clock:
        return self._clock

    def create_rotation(self, config: RotationConfig) -> RotationState:
        with self._lock:
            name = config.credential_name
            if self._store.load(name) is not None:
                raise RotationAlreadyExistsError(f"rotation '{name}' already exists")

            state = RotationState(
                name=name,
                config=config,
                phase=RotationPhase.IDLE,
                traffic_stats=TrafficStats(),
            )

            self._router.register_rotation(
                rotation_name=name,
                old_credential=config.old_credential,
                new_credential=config.new_credential,
            )

            self._store.save(state)
            return state

    def start_dual_write(self, name: str) -> RotationState:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase != RotationPhase.IDLE:
                raise InvalidRotationPhaseError(
                    f"cannot start dual write in phase {state.phase.value}"
                )

            state.phase = RotationPhase.DUAL_WRITE
            state.dual_write_started_at = self._clock.now()
            state.current_traffic_percentage = 0
            self._router.set_traffic_percentage(name, 0)

            self._store.save(state)
            return state

    def check_dual_write_complete(self, name: str) -> bool:
        with self._lock:
            state = self._get_state_or_raise(name)
            if state.phase != RotationPhase.DUAL_WRITE:
                return False
            if state.dual_write_started_at is None:
                return False
            elapsed = self._clock.now() - state.dual_write_started_at
            return elapsed >= state.config.dual_write_duration_seconds

    def start_canary(self, name: str) -> RotationState:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase not in (RotationPhase.DUAL_WRITE, RotationPhase.COOLDOWN):
                raise InvalidRotationPhaseError(
                    f"cannot start canary in phase {state.phase.value}"
                )

            if state.phase == RotationPhase.DUAL_WRITE:
                if not self.check_dual_write_complete(name):
                    raise InvalidRotationPhaseError(
                        "dual write period has not yet elapsed"
                    )

            if state.phase == RotationPhase.COOLDOWN:
                if not self.check_cooldown_complete(name):
                    raise InvalidRotationPhaseError(
                        "cooldown period has not yet elapsed"
                    )

            state.phase = RotationPhase.CANARY
            state.canary_started_at = self._clock.now()
            if state.current_traffic_percentage == 0:
                state.current_traffic_percentage = state.config.traffic_step_percentage
                if state.current_traffic_percentage > state.max_traffic_reached:
                    state.max_traffic_reached = state.current_traffic_percentage
                self._router.set_traffic_percentage(name, state.current_traffic_percentage)
            else:
                self._router.set_traffic_percentage(name, state.current_traffic_percentage)

            self._store.save(state)
            return state

    def advance_traffic(self, name: str) -> RotationState:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase != RotationPhase.CANARY:
                raise InvalidRotationPhaseError(
                    f"cannot advance traffic in phase {state.phase.value}"
                )

            next_pct = state.current_traffic_percentage + state.config.traffic_step_percentage
            if next_pct >= 100:
                next_pct = 100

            state.current_traffic_percentage = next_pct
            if next_pct > state.max_traffic_reached:
                state.max_traffic_reached = next_pct
            self._router.set_traffic_percentage(name, next_pct)

            if next_pct == 100:
                self._complete_rotation(state)

            self._store.save(state)
            return state

    def set_traffic_percentage(self, name: str, percentage: int) -> RotationState:
        if percentage < 0 or percentage > 100:
            raise InvalidTrafficPercentageError(
                "traffic percentage must be between 0 and 100"
            )

        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase not in (RotationPhase.CANARY, RotationPhase.COOLDOWN):
                raise InvalidRotationPhaseError(
                    f"cannot set traffic percentage in phase {state.phase.value}"
                )

            state.current_traffic_percentage = percentage
            if percentage > state.max_traffic_reached:
                state.max_traffic_reached = percentage
            self._router.set_traffic_percentage(name, percentage)

            if state.phase == RotationPhase.COOLDOWN and percentage > 0:
                state.phase = RotationPhase.CANARY

            if percentage == 100:
                self._complete_rotation(state)

            self._store.save(state)
            return state

    def complete_rotation(self, name: str) -> RotationState:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase not in (RotationPhase.CANARY, RotationPhase.DUAL_WRITE):
                raise InvalidRotationPhaseError(
                    f"cannot complete rotation in phase {state.phase.value}"
                )

            self._complete_rotation(state)
            self._store.save(state)
            return state

    def manual_rollback(self, name: str, reason: str = "Manual rollback") -> RotationState:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase in (RotationPhase.COMPLETED, RotationPhase.ROLLED_BACK, RotationPhase.IDLE):
                raise InvalidRotationPhaseError(
                    f"cannot rollback in phase {state.phase.value}"
                )

            traffic_before = state.current_traffic_percentage
            self._perform_fallback(
                state=state,
                reason=FallbackReason.MANUAL,
                failure_count=0,
                detail=reason,
            )

            state.phase = RotationPhase.ROLLED_BACK
            state.rolled_back_at = self._clock.now()
            self._router.set_traffic_percentage(name, 0)
            self._store.save(state)
            return state

    def evaluate_canary_health(self, name: str) -> Tuple[bool, Optional[FallbackRecord]]:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase != RotationPhase.CANARY:
                raise InvalidRotationPhaseError(
                    f"cannot evaluate health in phase {state.phase.value}"
                )

            stats = self._router.get_stats(name)
            state.traffic_stats = stats

            if stats.new_consecutive_failures >= state.config.consecutive_failure_threshold:
                record = self._perform_fallback(
                    state=state,
                    reason=FallbackReason.CONSECUTIVE_FAILURES,
                    failure_count=stats.new_consecutive_failures,
                    detail=(
                        f"Consecutive failures {stats.new_consecutive_failures} "
                        f"exceeds threshold {state.config.consecutive_failure_threshold}"
                    ),
                )
                self._store.save(state)
                return False, record

            if stats.new_requests >= state.config.min_requests_for_evaluation:
                if stats.new_error_rate > state.config.max_error_rate:
                    record = self._perform_fallback(
                        state=state,
                        reason=FallbackReason.ERROR_RATE_EXCEEDED,
                        failure_count=stats.new_errors,
                        detail=(
                            f"Error rate {stats.new_error_rate:.4f} exceeds "
                            f"threshold {state.config.max_error_rate:.4f}"
                        ),
                    )
                    self._store.save(state)
                    return False, record

            self._store.save(state)
            return True, None

    def check_cooldown_complete(self, name: str) -> bool:
        with self._lock:
            state = self._get_state_or_raise(name)
            if state.phase != RotationPhase.COOLDOWN:
                return False
            if state.cooldown_started_at is None:
                return False
            elapsed = self._clock.now() - state.cooldown_started_at
            return elapsed >= state.config.cooldown_seconds

    def try_auto_recover(self, name: str) -> bool:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase != RotationPhase.COOLDOWN:
                return False
            if not state.config.auto_recover_enabled:
                return False
            if not self.check_cooldown_complete(name):
                return False

            recover_pct = max(
                state.config.traffic_step_percentage,
                state.current_traffic_percentage,
            )
            if recover_pct > state.max_traffic_reached:
                recover_pct = state.max_traffic_reached
            if recover_pct <= 0:
                recover_pct = state.config.traffic_step_percentage

            state.phase = RotationPhase.CANARY
            state.canary_started_at = self._clock.now()
            state.current_traffic_percentage = recover_pct
            state.cooldown_started_at = None
            self._router.reset_stats(name)
            state.traffic_stats = TrafficStats()
            self._router.set_traffic_percentage(name, recover_pct)

            self._store.save(state)
            return True

    def perform_write(self, name: str, data: Optional[dict] = None) -> WriteResult:
        if data is None:
            data = {}

        with self._lock:
            state = self._get_state_or_raise(name)
            now = self._clock.now()

            old_success = True
            new_success = True
            old_error: Optional[str] = None
            new_error: Optional[str] = None

            should_write_old = state.phase in (
                RotationPhase.DUAL_WRITE,
                RotationPhase.CANARY,
                RotationPhase.COOLDOWN,
                RotationPhase.ROLLED_BACK,
            )
            should_write_new = state.phase in (
                RotationPhase.DUAL_WRITE,
                RotationPhase.CANARY,
                RotationPhase.COOLDOWN,
                RotationPhase.COMPLETED,
                RotationPhase.ROLLED_BACK,
            )

            if should_write_old:
                try:
                    self._write_target.write_old(state.config.old_credential, data)
                except Exception as e:
                    old_success = False
                    old_error = str(e)
                    record = WriteFailureRecord(
                        timestamp=now,
                        side=WriteSide.OLD,
                        error_message=old_error,
                    )
                    state.write_failure_records.append(record)

            if should_write_new:
                try:
                    self._write_target.write_new(state.config.new_credential, data)
                except Exception as e:
                    new_success = False
                    new_error = str(e)
                    record = WriteFailureRecord(
                        timestamp=now,
                        side=WriteSide.NEW,
                        error_message=new_error,
                    )
                    state.write_failure_records.append(record)

            if not should_write_old:
                old_success = False
            if not should_write_new:
                new_success = False

            self._store.save(state)

            return WriteResult(
                old_success=old_success,
                new_success=new_success,
                old_error=old_error,
                new_error=new_error,
            )

    def route_read(
        self,
        name: str,
        request_key: str,
    ) -> Tuple[str, CredentialVersion]:
        with self._lock:
            state = self._get_state_or_raise(name)

            if state.phase == RotationPhase.IDLE:
                raise InvalidRotationPhaseError(
                    f"cannot route read in phase {state.phase.value}"
                )

            if state.phase == RotationPhase.COMPLETED:
                credential, version = self._router.route(
                    name, request_key, force_version=CredentialVersion.NEW
                )
                return credential, version

            if state.phase == RotationPhase.ROLLED_BACK:
                credential, version = self._router.route(
                    name, request_key, force_version=CredentialVersion.OLD
                )
                return credential, version

            if state.phase == RotationPhase.DUAL_WRITE:
                credential, version = self._router.route(
                    name, request_key, force_version=CredentialVersion.OLD
                )
                return credential, version

            if state.phase == RotationPhase.COOLDOWN:
                credential, version = self._router.route(
                    name, request_key, force_version=CredentialVersion.OLD
                )
                return credential, version

            return self._router.route(name, request_key)

    def record_request_result(
        self,
        name: str,
        version: CredentialVersion,
        is_error: bool = False,
    ) -> Optional[FallbackRecord]:
        with self._lock:
            state = self._get_state_or_raise(name)
            self._router.record_metrics(name, version, is_error)
            state.traffic_stats = self._router.get_stats(name)

            if state.phase != RotationPhase.CANARY:
                self._store.save(state)
                return None

            if (
                version == CredentialVersion.NEW
                and state.traffic_stats.new_consecutive_failures
                >= state.config.consecutive_failure_threshold
            ):
                record = self._perform_fallback(
                    state=state,
                    reason=FallbackReason.CONSECUTIVE_FAILURES,
                    failure_count=state.traffic_stats.new_consecutive_failures,
                    detail=(
                        f"Consecutive failures {state.traffic_stats.new_consecutive_failures} "
                        f"reaches threshold {state.config.consecutive_failure_threshold}"
                    ),
                )
                self._store.save(state)
                return record

            self._store.save(state)
            return None

    def get_state(self, name: str) -> RotationState:
        with self._lock:
            return self._get_state_or_raise(name)

    def list_rotations(self) -> list[RotationState]:
        with self._lock:
            return self._store.list_all()

    def get_stats(self, name: str) -> TrafficStats:
        self._get_state_or_raise(name)
        return self._router.get_stats(name)

    def get_fallback_history(self, name: str) -> list[FallbackRecord]:
        state = self._get_state_or_raise(name)
        return list(state.fallback_records)

    def get_write_failure_history(self, name: str) -> list[WriteFailureRecord]:
        state = self._get_state_or_raise(name)
        return list(state.write_failure_records)

    def reset_stats(self, name: str) -> None:
        with self._lock:
            self._get_state_or_raise(name)
            self._router.reset_stats(name)

    def serialize_state(self, name: str) -> str:
        with self._lock:
            self._get_state_or_raise(name)
            return self._store.to_json(name)

    def restore_from_serialized(self, json_str: str) -> RotationState:
        with self._lock:
            state = self._store.from_json(json_str)
            try:
                self._router.register_rotation(
                    rotation_name=state.name,
                    old_credential=state.config.old_credential,
                    new_credential=state.config.new_credential,
                )
            except Exception:
                pass
            self._router.set_traffic_percentage(state.name, state.current_traffic_percentage)
            self._sync_router_stats(state)
            return state

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return self._store.snapshot_all()

    def restore(self, snapshots: dict[str, str]) -> None:
        with self._lock:
            self._store.restore_all(snapshots)
            for name in snapshots:
                state = self._store.load(name)
                if state is not None:
                    try:
                        self._router.register_rotation(
                            rotation_name=state.name,
                            old_credential=state.config.old_credential,
                            new_credential=state.config.new_credential,
                        )
                    except Exception:
                        pass
                    self._router.set_traffic_percentage(state.name, state.current_traffic_percentage)
                    self._sync_router_stats(state)

    def _sync_router_stats(self, state: RotationState) -> None:
        self._router.reset_stats(state.name)
        stats = state.traffic_stats
        for _ in range(stats.old_requests):
            self._router.record_old_metrics(state.name, is_error=False)
        for _ in range(stats.old_errors):
            self._router.record_old_metrics(state.name, is_error=True)
        for _ in range(stats.new_requests - stats.new_errors):
            self._router.record_new_metrics(state.name, is_error=False)
        for _ in range(stats.new_errors):
            self._router.record_new_metrics(state.name, is_error=True)

    def _complete_rotation(self, state: RotationState) -> None:
        state.phase = RotationPhase.COMPLETED
        state.completed_at = self._clock.now()
        state.current_traffic_percentage = 100
        self._router.set_traffic_percentage(state.name, 100)

    def _perform_fallback(
        self,
        state: RotationState,
        reason: FallbackReason,
        failure_count: int,
        detail: str,
    ) -> FallbackRecord:
        traffic_before = state.current_traffic_percentage
        now = self._clock.now()

        record = FallbackRecord(
            timestamp=now,
            reason=reason,
            traffic_percentage_at_fallback=traffic_before,
            failure_count=failure_count,
            detail=detail,
        )
        state.fallback_records.append(record)

        state.phase = RotationPhase.COOLDOWN
        state.cooldown_started_at = now
        state.current_traffic_percentage = 0
        self._router.set_traffic_percentage(state.name, 0)

        return record

    def _get_state_or_raise(self, name: str) -> RotationState:
        state = self._store.load(name)
        if state is None:
            raise RotationNotFoundError(f"rotation '{name}' not found")
        return state
