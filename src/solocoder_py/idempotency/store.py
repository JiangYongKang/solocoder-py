from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

from .clock import Clock, SystemClock
from .exceptions import (
    IdempotencyError,
    IdempotencyKeyConflictError,
    IdempotencyKeyExpiredError,
    IdempotencyKeyMismatchError,
    IdempotencyProcessingError,
)
from .models import FailureReplayPolicy, IdempotencyRecord, IdempotencyState


@dataclass
class IdempotencyResult:
    record: IdempotencyRecord
    is_replay: bool
    should_execute: bool

    @property
    def state(self) -> IdempotencyState:
        return self.record.state

    @property
    def response_data(self) -> Optional[Any]:
        return self.record.response_data

    @property
    def error_message(self) -> Optional[str]:
        return self.record.error_message


@dataclass
class _RecordHolder:
    record: IdempotencyRecord
    ready: threading.Event = field(default_factory=threading.Event)


@dataclass
class IdempotencyStore:
    _records: Dict[str, _RecordHolder] = field(default_factory=dict)
    _global_lock: threading.RLock = field(default_factory=threading.RLock)
    _clock: Clock = field(default_factory=SystemClock)
    default_ttl_seconds: float = 86400.0
    failure_replay_policy: FailureReplayPolicy = FailureReplayPolicy.REJECT
    wait_timeout_seconds: float = 30.0
    wait_poll_interval_seconds: float = 0.05

    def __post_init__(self) -> None:
        if self.default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        if self.wait_timeout_seconds <= 0:
            raise ValueError("wait_timeout_seconds must be positive")
        if self.wait_poll_interval_seconds <= 0:
            raise ValueError("wait_poll_interval_seconds must be positive")

    def _is_expired(self, record: IdempotencyRecord) -> bool:
        return record.is_expired(self._clock)

    def _expire_if_needed(self, holder: _RecordHolder) -> None:
        if self._is_expired(holder.record):
            holder.record.mark_expired()

    def _acquire_or_wait(
        self,
        key: str,
        request_fingerprint: str,
        ttl_seconds: Optional[float] = None,
    ) -> Tuple[Optional[_RecordHolder], IdempotencyResult]:
        effective_ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        deadline = self._clock.now() + self.wait_timeout_seconds

        while True:
            with self._global_lock:
                holder = self._records.get(key)

                if holder is None:
                    now = self._clock.now()
                    new_record = IdempotencyRecord(
                        key=key,
                        request_fingerprint=request_fingerprint,
                        created_at=now,
                        expires_at=now + effective_ttl,
                    )
                    new_holder = _RecordHolder(record=new_record)
                    self._records[key] = new_holder
                    return new_holder, IdempotencyResult(
                        record=new_record.snapshot(),
                        is_replay=False,
                        should_execute=True,
                    )

                self._expire_if_needed(holder)

                if holder.record.state == IdempotencyState.EXPIRED:
                    now = self._clock.now()
                    new_record = IdempotencyRecord(
                        key=key,
                        request_fingerprint=request_fingerprint,
                        created_at=now,
                        expires_at=now + effective_ttl,
                    )
                    holder.record = new_record
                    holder.ready.clear()
                    return holder, IdempotencyResult(
                        record=new_record.snapshot(),
                        is_replay=False,
                        should_execute=True,
                    )

                if not holder.record.fingerprint_matches(request_fingerprint):
                    raise IdempotencyKeyMismatchError(
                        f"Idempotency key '{key}' already bound to a different request fingerprint"
                    )

                if holder.record.state == IdempotencyState.SUCCESS:
                    return None, IdempotencyResult(
                        record=holder.record.snapshot(),
                        is_replay=True,
                        should_execute=False,
                    )

                if holder.record.state == IdempotencyState.FAILED:
                    if self.failure_replay_policy == FailureReplayPolicy.REPLAY:
                        return None, IdempotencyResult(
                            record=holder.record.snapshot(),
                            is_replay=True,
                            should_execute=False,
                        )
                    elif self.failure_replay_policy == FailureReplayPolicy.REJECT:
                        raise IdempotencyProcessingError(
                            f"Idempotency key '{key}' has a recorded failure: {holder.record.error_message}"
                        )
                    elif self.failure_replay_policy == FailureReplayPolicy.RETRY:
                        holder.record.state = IdempotencyState.PROCESSING
                        holder.record.error_message = None
                        holder.record.response_data = None
                        holder.record.refresh_ttl(effective_ttl, self._clock)
                        holder.ready.clear()
                        return holder, IdempotencyResult(
                            record=holder.record.snapshot(),
                            is_replay=False,
                            should_execute=True,
                        )

                if holder.record.state == IdempotencyState.PROCESSING:
                    ready_event = holder.ready

            remaining = deadline - self._clock.now()
            if remaining <= 0:
                raise IdempotencyKeyConflictError(
                    f"Timed out waiting for idempotency key '{key}' processing to complete"
                )
            wait_for = min(remaining, self.wait_poll_interval_seconds)
            ready_event.wait(timeout=wait_for)

    def begin_request(
        self,
        key: str,
        request_fingerprint: str,
        ttl_seconds: Optional[float] = None,
    ) -> IdempotencyResult:
        if not key:
            raise ValueError("key cannot be empty")
        if not request_fingerprint:
            raise ValueError("request_fingerprint cannot be empty")
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        _, result = self._acquire_or_wait(key, request_fingerprint, ttl_seconds)
        return result

    def complete_success(
        self,
        key: str,
        request_fingerprint: str,
        response_data: Any,
    ) -> IdempotencyResult:
        if not key:
            raise ValueError("key cannot be empty")
        if not request_fingerprint:
            raise ValueError("request_fingerprint cannot be empty")

        with self._global_lock:
            holder = self._records.get(key)
            if holder is None:
                raise IdempotencyError(f"Idempotency key '{key}' not found")

            self._expire_if_needed(holder)

            if holder.record.state == IdempotencyState.EXPIRED:
                raise IdempotencyKeyExpiredError(
                    f"Idempotency key '{key}' has expired"
                )

            if not holder.record.fingerprint_matches(request_fingerprint):
                raise IdempotencyKeyMismatchError(
                    f"Idempotency key '{key}' bound to a different fingerprint"
                )

            if holder.record.state != IdempotencyState.PROCESSING:
                raise IdempotencyError(
                    f"Cannot complete success from state {holder.record.state}"
                )

            holder.record.mark_success(response_data)
            holder.ready.set()

            return IdempotencyResult(
                record=holder.record.snapshot(),
                is_replay=False,
                should_execute=False,
            )

    def complete_failure(
        self,
        key: str,
        request_fingerprint: str,
        error_message: str,
    ) -> IdempotencyResult:
        if not key:
            raise ValueError("key cannot be empty")
        if not request_fingerprint:
            raise ValueError("request_fingerprint cannot be empty")
        if not error_message:
            raise ValueError("error_message cannot be empty")

        with self._global_lock:
            holder = self._records.get(key)
            if holder is None:
                raise IdempotencyError(f"Idempotency key '{key}' not found")

            self._expire_if_needed(holder)

            if holder.record.state == IdempotencyState.EXPIRED:
                raise IdempotencyKeyExpiredError(
                    f"Idempotency key '{key}' has expired"
                )

            if not holder.record.fingerprint_matches(request_fingerprint):
                raise IdempotencyKeyMismatchError(
                    f"Idempotency key '{key}' bound to a different fingerprint"
                )

            if holder.record.state != IdempotencyState.PROCESSING:
                raise IdempotencyError(
                    f"Cannot complete failure from state {holder.record.state}"
                )

            holder.record.mark_failed(error_message)
            holder.ready.set()

            return IdempotencyResult(
                record=holder.record.snapshot(),
                is_replay=False,
                should_execute=False,
            )

    def execute_with_idempotency(
        self,
        key: str,
        request_fingerprint: str,
        operation: Callable[[], Any],
        ttl_seconds: Optional[float] = None,
    ) -> IdempotencyResult:
        if not callable(operation):
            raise ValueError("operation must be callable")

        result = self.begin_request(key, request_fingerprint, ttl_seconds)

        if not result.should_execute:
            return result

        try:
            response_data = operation()
            return self.complete_success(key, request_fingerprint, response_data)
        except Exception as e:
            self.complete_failure(key, request_fingerprint, str(e))
            raise

    def get_record(self, key: str) -> Optional[IdempotencyRecord]:
        if not key:
            raise ValueError("key cannot be empty")

        with self._global_lock:
            holder = self._records.get(key)
            if holder is None:
                return None
            self._expire_if_needed(holder)
            return holder.record.snapshot()

    def exists(self, key: str) -> bool:
        return self.get_record(key) is not None

    def invalidate(self, key: str) -> bool:
        if not key:
            raise ValueError("key cannot be empty")

        with self._global_lock:
            if key in self._records:
                del self._records[key]
                return True
            return False

    def clear(self) -> None:
        with self._global_lock:
            self._records.clear()

    def count(self) -> int:
        with self._global_lock:
            return len(self._records)

    def cleanup_expired(self) -> int:
        with self._global_lock:
            expired_keys = []
            for key, holder in self._records.items():
                if holder.record.state == IdempotencyState.PROCESSING:
                    continue
                if self._is_expired(holder.record):
                    expired_keys.append(key)
            for key in expired_keys:
                del self._records[key]
            return len(expired_keys)
