from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from .exceptions import (
    InvalidFenceTokenError,
    LockAcquisitionTimeoutError,
    LockError,
    LockExpiredError,
    LockNotAcquiredError,
    LockNotHeldError,
)
from .models import LockEntry, LockState


@dataclass
class DistributedLockManager:
    _locks: Dict[str, LockEntry] = field(default_factory=dict)
    _next_fence_token: int = 1
    _lock: threading.Lock = field(default_factory=threading.Lock)
    default_lease_duration: timedelta = field(default_factory=lambda: timedelta(seconds=30))

    def __post_init__(self) -> None:
        if self.default_lease_duration.total_seconds() <= 0:
            raise ValueError("default_lease_duration must be positive")

    def _generate_fence_token(self) -> int:
        token = self._next_fence_token
        self._next_fence_token += 1
        return token

    def _get_or_create_entry(self, lock_name: str) -> LockEntry:
        if lock_name not in self._locks:
            self._locks[lock_name] = LockEntry(lock_name=lock_name)
        return self._locks[lock_name]

    def acquire(
        self,
        lock_name: str,
        client_id: str,
        lease_duration: Optional[timedelta] = None,
        timeout: Optional[timedelta] = None,
        retry_interval: Optional[timedelta] = None,
    ) -> int:
        if not lock_name:
            raise ValueError("lock_name cannot be empty")
        if not client_id:
            raise ValueError("client_id cannot be empty")

        retry = retry_interval if retry_interval is not None else timedelta(milliseconds=50)

        duration = lease_duration if lease_duration is not None else self.default_lease_duration
        if duration.total_seconds() <= 0:
            raise ValueError("lease_duration must be positive")

        deadline: Optional[datetime] = None
        if timeout is not None:
            if timeout.total_seconds() <= 0:
                raise ValueError("timeout must be positive")
            deadline = datetime.now() + timeout

        while True:
            with self._lock:
                entry = self._get_or_create_entry(lock_name)

                if entry.is_expired:
                    entry.mark_expired()
                    entry.force_release()

                if entry.state == LockState.FREE:
                    token = self._generate_fence_token()
                    entry.acquire(client_id, token, duration)
                    return token

                if entry.is_held_by(client_id):
                    entry.reenter(duration)
                    return entry.fence_token

                if deadline is None:
                    raise LockNotAcquiredError(
                        f"Lock '{lock_name}' is held by another client"
                    )

            if datetime.now() >= deadline:
                raise LockAcquisitionTimeoutError(
                    f"Timed out waiting to acquire lock '{lock_name}'"
                )

            time.sleep(retry.total_seconds())

    def try_acquire(
        self,
        lock_name: str,
        client_id: str,
        lease_duration: Optional[timedelta] = None,
    ) -> Optional[int]:
        try:
            return self.acquire(lock_name, client_id, lease_duration=lease_duration)
        except LockNotAcquiredError:
            return None

    def release(
        self,
        lock_name: str,
        client_id: str,
        fence_token: int,
    ) -> bool:
        if not lock_name:
            raise ValueError("lock_name cannot be empty")
        if not client_id:
            raise ValueError("client_id cannot be empty")
        if fence_token <= 0:
            raise ValueError("fence_token must be positive")

        with self._lock:
            entry = self._locks.get(lock_name)
            if entry is None:
                raise LockNotHeldError(f"Lock '{lock_name}' is not held")

            if entry.state == LockState.FREE:
                raise LockNotHeldError(f"Lock '{lock_name}' is not held")

            if entry.is_expired:
                entry.mark_expired()
                token_match = entry.fence_token == fence_token
                client_match = entry.client_id == client_id
                if token_match and client_match:
                    raise LockExpiredError(f"Lock '{lock_name}' has expired")
                if not token_match:
                    raise InvalidFenceTokenError(
                        f"Invalid fence token for lock '{lock_name}': "
                        f"expected {entry.fence_token}, got {fence_token}"
                    )
                raise LockNotHeldError(
                    f"Lock '{lock_name}' is not held by client '{client_id}'"
                )

            if entry.fence_token != fence_token:
                raise InvalidFenceTokenError(
                    f"Invalid fence token for lock '{lock_name}': "
                    f"expected {entry.fence_token}, got {fence_token}"
                )

            if entry.client_id != client_id:
                raise LockNotHeldError(
                    f"Lock '{lock_name}' is not held by client '{client_id}'"
                )

            fully_released = entry.release_one()
            return fully_released

    def renew(
        self,
        lock_name: str,
        client_id: str,
        fence_token: int,
        lease_duration: Optional[timedelta] = None,
    ) -> timedelta:
        if not lock_name:
            raise ValueError("lock_name cannot be empty")
        if not client_id:
            raise ValueError("client_id cannot be empty")
        if fence_token <= 0:
            raise ValueError("fence_token must be positive")

        duration = lease_duration if lease_duration is not None else self.default_lease_duration
        if duration.total_seconds() <= 0:
            raise ValueError("lease_duration must be positive")

        with self._lock:
            entry = self._locks.get(lock_name)
            if entry is None:
                raise LockNotHeldError(f"Lock '{lock_name}' is not held")

            if entry.state == LockState.FREE:
                raise LockNotHeldError(f"Lock '{lock_name}' is not held")

            if entry.is_expired:
                entry.mark_expired()
                token_match = entry.fence_token == fence_token
                client_match = entry.client_id == client_id
                if token_match and client_match:
                    raise LockExpiredError(f"Lock '{lock_name}' has expired")
                if not token_match:
                    raise InvalidFenceTokenError(
                        f"Invalid fence token for lock '{lock_name}': "
                        f"expected {entry.fence_token}, got {fence_token}"
                    )
                raise LockNotHeldError(
                    f"Lock '{lock_name}' is not held by client '{client_id}'"
                )

            if entry.fence_token != fence_token:
                raise InvalidFenceTokenError(
                    f"Invalid fence token for lock '{lock_name}': "
                    f"expected {entry.fence_token}, got {fence_token}"
                )

            if entry.client_id != client_id:
                raise LockNotHeldError(
                    f"Lock '{lock_name}' is not held by client '{client_id}'"
                )

            entry.renew(duration)
            return duration

    def validate_fence_token(
        self,
        lock_name: str,
        fence_token: int,
    ) -> bool:
        with self._lock:
            entry = self._locks.get(lock_name)
            if entry is None or entry.state == LockState.FREE:
                return False
            if entry.is_expired:
                return False
            return entry.fence_token == fence_token and entry.is_held

    def get_lock_info(self, lock_name: str) -> Optional[LockEntry]:
        with self._lock:
            entry = self._locks.get(lock_name)
            if entry is None:
                return None
            effective_state = entry.state
            if entry.is_expired and entry.state != LockState.EXPIRED:
                effective_state = LockState.EXPIRED
            return LockEntry(
                lock_name=entry.lock_name,
                state=effective_state,
                client_id=entry.client_id,
                fence_token=entry.fence_token,
                reentrant_count=entry.reentrant_count,
                lease_expires_at=entry.lease_expires_at,
                acquired_at=entry.acquired_at,
                lease_duration=entry.lease_duration,
            )

    def is_held(self, lock_name: str) -> bool:
        with self._lock:
            entry = self._locks.get(lock_name)
            if entry is None:
                return False
            return entry.is_held

    def is_held_by(self, lock_name: str, client_id: str) -> bool:
        with self._lock:
            entry = self._locks.get(lock_name)
            if entry is None:
                return False
            return entry.is_held_by(client_id)

    def force_release(self, lock_name: str) -> bool:
        with self._lock:
            entry = self._locks.get(lock_name)
            if entry is None or entry.state == LockState.FREE:
                return False
            entry.force_release()
            return True

    def clear(self) -> None:
        with self._lock:
            self._locks.clear()

    def count(self) -> int:
        with self._lock:
            return sum(1 for e in self._locks.values() if e.is_held)
