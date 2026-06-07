from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple

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
    condition: threading.Condition = field(default_factory=threading.Condition)


@dataclass
class IdempotencyStore:
    _records: Dict[str, _RecordHolder] = field(default_factory=dict)
    _global_lock: threading.RLock = field(default_factory=threading.RLock)
    default_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))
    failure_replay_policy: FailureReplayPolicy = FailureReplayPolicy.REJECT
    wait_timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    wait_poll_interval: timedelta = field(default_factory=lambda: timedelta(milliseconds=50))

    def __post_init__(self) -> None:
        if self.default_ttl.total_seconds() <= 0:
            raise ValueError("default_ttl must be positive")
        if self.wait_timeout.total_seconds() <= 0:
            raise ValueError("wait_timeout must be positive")
        if self.wait_poll_interval.total_seconds() <= 0:
            raise ValueError("wait_poll_interval must be positive")

    def _is_expired(self, record: IdempotencyRecord) -> bool:
        if record.state == IdempotencyState.EXPIRED:
            return True
        return datetime.now() >= record.expires_at

    def _expire_if_needed(self, holder: _RecordHolder) -> None:
        if self._is_expired(holder.record):
            holder.record.mark_expired()

    def _acquire_or_wait(
        self,
        key: str,
        request_fingerprint: str,
        ttl: Optional[timedelta] = None,
    ) -> Tuple[Optional[_RecordHolder], IdempotencyResult]:
        effective_ttl = ttl if ttl is not None else self.default_ttl

        deadline = datetime.now() + self.wait_timeout

        while True:
            with self._global_lock:
                holder = self._records.get(key)

                if holder is None:
                    new_record = IdempotencyRecord(
                        key=key,
                        request_fingerprint=request_fingerprint,
                        expires_at=datetime.now() + effective_ttl,
                    )
                    new_holder = _RecordHolder(record=new_record)
                    self._records[key] = new_holder
                    return new_holder, IdempotencyResult(
                        record=new_record,
                        is_replay=False,
                        should_execute=True,
                    )

                self._expire_if_needed(holder)

                if holder.record.state == IdempotencyState.EXPIRED:
                    new_record = IdempotencyRecord(
                        key=key,
                        request_fingerprint=request_fingerprint,
                        expires_at=datetime.now() + effective_ttl,
                    )
                    holder.record = new_record
                    return holder, IdempotencyResult(
                        record=new_record,
                        is_replay=False,
                        should_execute=True,
                    )

                if not holder.record.fingerprint_matches(request_fingerprint):
                    raise IdempotencyKeyMismatchError(
                        f"Idempotency key '{key}' already bound to a different request fingerprint"
                    )

                if holder.record.state == IdempotencyState.SUCCESS:
                    return None, IdempotencyResult(
                        record=holder.record,
                        is_replay=True,
                        should_execute=False,
                    )

                if holder.record.state == IdempotencyState.FAILED:
                    if self.failure_replay_policy == FailureReplayPolicy.REPLAY:
                        return None, IdempotencyResult(
                            record=holder.record,
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
                        holder.record.refresh_ttl(effective_ttl)
                        return holder, IdempotencyResult(
                            record=holder.record,
                            is_replay=False,
                            should_execute=True,
                        )

                if holder.record.state == IdempotencyState.PROCESSING:
                    condition = holder.condition

            with condition:
                if holder.record.state == IdempotencyState.PROCESSING:
                    remaining = (deadline - datetime.now()).total_seconds()
                    if remaining <= 0:
                        raise IdempotencyKeyConflictError(
                            f"Timed out waiting for idempotency key '{key}' processing to complete"
                        )
                    wait_time = min(remaining, self.wait_poll_interval.total_seconds())
                    condition.wait(timeout=wait_time)

    def begin_request(
        self,
        key: str,
        request_fingerprint: str,
        ttl: Optional[timedelta] = None,
    ) -> IdempotencyResult:
        if not key:
            raise ValueError("key cannot be empty")
        if not request_fingerprint:
            raise ValueError("request_fingerprint cannot be empty")
        if ttl is not None and ttl.total_seconds() <= 0:
            raise ValueError("ttl must be positive")

        _, result = self._acquire_or_wait(key, request_fingerprint, ttl)
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

            with holder.condition:
                holder.condition.notify_all()

            return IdempotencyResult(
                record=holder.record,
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

            with holder.condition:
                holder.condition.notify_all()

            return IdempotencyResult(
                record=holder.record,
                is_replay=False,
                should_execute=False,
            )

    def execute_with_idempotency(
        self,
        key: str,
        request_fingerprint: str,
        operation: Callable[[], Any],
        ttl: Optional[timedelta] = None,
    ) -> IdempotencyResult:
        if not callable(operation):
            raise ValueError("operation must be callable")

        result = self.begin_request(key, request_fingerprint, ttl)

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
            record = holder.record
            return IdempotencyRecord(
                key=record.key,
                request_fingerprint=record.request_fingerprint,
                state=record.state,
                response_data=record.response_data,
                error_message=record.error_message,
                created_at=record.created_at,
                expires_at=record.expires_at,
            )

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
                if self._is_expired(holder.record):
                    expired_keys.append(key)
            for key in expired_keys:
                del self._records[key]
            return len(expired_keys)
