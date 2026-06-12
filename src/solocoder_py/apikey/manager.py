from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, FrozenSet, List, Optional, Set, Tuple

from .exceptions import (
    APIKeyError,
    APIKeyNotFoundError,
    APIKeyPermissionDeniedError,
    APIKeyPrefixCollisionError,
    APIKeyRevokedError,
    InvalidAPIKeyError,
)
from .models import (
    APIKey,
    APIKeyCreateResult,
    APIKeyInfo,
    Clock,
    Scope,
    ScopeRegistry,
    UsageStats,
    generate_key_id,
    generate_key_secret,
    get_key_prefix,
    hash_key_secret,
)


@dataclass
class _UsageWindow:
    timestamps: Deque[float] = field(default_factory=deque)
    window_seconds: float = 3600.0

    def record(self, now: float) -> None:
        self.timestamps.append(now)
        self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def count(self, now: float) -> int:
        self._prune(now)
        return len(self.timestamps)


@dataclass
class _KeyRecord:
    key: APIKey
    key_hash: str
    total_uses: int = 0
    last_used_at: Optional[float] = None
    usage_window: _UsageWindow = field(default_factory=_UsageWindow)


class APIKeyManager:
    _keys_by_id: Dict[str, _KeyRecord]
    _keys_by_hash: Dict[str, str]
    _keys_by_subject: Dict[str, Set[str]]
    _prefix_index: Dict[str, Set[str]]
    _scope_registry: ScopeRegistry
    _lock: threading.RLock
    _clock: Clock
    _prefix_length: int
    _idle_threshold_days: float
    _window_seconds: float

    def __init__(
        self,
        scope_registry: Optional[ScopeRegistry] = None,
        clock: Optional[Clock] = None,
        prefix_length: int = 8,
        idle_threshold_days: float = 30.0,
        window_seconds: float = 3600.0,
    ) -> None:
        if prefix_length <= 0:
            raise ValueError("prefix_length must be positive")
        if idle_threshold_days <= 0:
            raise ValueError("idle_threshold_days must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self._keys_by_id = {}
        self._keys_by_hash = {}
        self._keys_by_subject = {}
        self._prefix_index = {}
        self._scope_registry = scope_registry or ScopeRegistry()
        self._lock = threading.RLock()
        self._clock = clock or Clock()
        self._prefix_length = prefix_length
        self._idle_threshold_days = idle_threshold_days
        self._window_seconds = window_seconds

    def register_scope(self, scope: str, implies: Optional[List[str]] = None) -> None:
        if not scope:
            raise ValueError("scope cannot be empty")
        with self._lock:
            self._scope_registry.register_scope(scope, implies)

    def _normalize_scopes(self, scopes: List) -> List[str]:
        normalized = []
        for s in scopes:
            if isinstance(s, Scope):
                normalized.append(s.name)
            elif isinstance(s, str):
                scope_obj = Scope(name=s)
                normalized.append(scope_obj.name)
            else:
                raise ValueError(
                    f"scope must be str or Scope, got {type(s).__name__}"
                )
        return normalized

    def _create_key_internal(
        self,
        subject: str,
        scope_names: List[str],
        key_length: int,
        key_secret_override: Optional[str] = None,
    ) -> APIKeyCreateResult:
        for _ in range(100):
            key_id = generate_key_id()
            if key_id not in self._keys_by_id:
                break
        else:
            raise APIKeyError("failed to generate unique key id")

        if key_secret_override is not None:
            key_secret = key_secret_override
            if len(key_secret) < 32:
                raise ValueError("key_secret_override must be at least 32 chars")
        else:
            key_secret = generate_key_secret(key_length)

        key_hash = hash_key_secret(key_secret)
        prefix = get_key_prefix(key_secret, self._prefix_length)

        if key_hash in self._keys_by_hash:
            raise APIKeyError("key hash collision detected")

        if prefix in self._prefix_index:
            existing_ids = self._prefix_index[prefix]
            for existing_id in existing_ids:
                existing_record = self._keys_by_id.get(existing_id)
                if existing_record and not existing_record.key.revoked:
                    raise APIKeyPrefixCollisionError(
                        f"key prefix collision: {prefix}"
                    )

        key = APIKey(
            key_id=key_id,
            subject=subject,
            scopes=frozenset(scope_names),
            prefix=prefix,
            created_at=self._clock.now(),
            revoked=False,
            revoked_at=None,
        )

        record = _KeyRecord(
            key=key,
            key_hash=key_hash,
            usage_window=_UsageWindow(window_seconds=self._window_seconds),
        )

        self._keys_by_id[key_id] = record
        self._keys_by_hash[key_hash] = key_id
        self._keys_by_subject.setdefault(subject, set()).add(key_id)
        self._prefix_index.setdefault(prefix, set()).add(key_id)

        return APIKeyCreateResult(
            key_id=key_id,
            subject=subject,
            scopes=frozenset(scope_names),
            key_secret=key_secret,
            prefix=prefix,
            created_at=key.created_at,
        )

    def create_key(
        self,
        subject: str,
        scopes: List,
        key_length: int = 48,
    ) -> APIKeyCreateResult:
        if not subject:
            raise ValueError("subject cannot be empty")
        if scopes is None:
            raise ValueError("scopes cannot be None")
        if key_length < 32:
            raise ValueError("key_length must be at least 32")

        scope_names = self._normalize_scopes(scopes)

        with self._lock:
            return self._create_key_internal(
                subject=subject,
                scope_names=scope_names,
                key_length=key_length,
                key_secret_override=None,
            )

    def create_key_with_secret(
        self,
        subject: str,
        scopes: List,
        key_secret: str,
    ) -> APIKeyCreateResult:
        if not subject:
            raise ValueError("subject cannot be empty")
        if scopes is None:
            raise ValueError("scopes cannot be None")
        if not key_secret or len(key_secret) < 32:
            raise ValueError("key_secret must be at least 32 characters")

        scope_names = self._normalize_scopes(scopes)

        with self._lock:
            return self._create_key_internal(
                subject=subject,
                scope_names=scope_names,
                key_length=len(key_secret),
                key_secret_override=key_secret,
            )

    def get_key(self, key_id: str) -> APIKeyInfo:
        if not key_id:
            raise ValueError("key_id cannot be empty")

        with self._lock:
            record = self._keys_by_id.get(key_id)
            if record is None:
                raise APIKeyNotFoundError(f"key not found: {key_id}")
            return self._make_key_info(record)

    def list_keys_by_subject(self, subject: str) -> List[APIKeyInfo]:
        if not subject:
            raise ValueError("subject cannot be empty")

        with self._lock:
            key_ids = self._keys_by_subject.get(subject, set())
            result = []
            for key_id in key_ids:
                record = self._keys_by_id.get(key_id)
                if record is not None:
                    result.append(self._make_key_info(record))
            return result

    def find_keys_by_prefix(self, prefix: str) -> List[APIKeyInfo]:
        if not prefix:
            raise ValueError("prefix cannot be empty")

        with self._lock:
            key_ids = self._prefix_index.get(prefix, set())
            result = []
            for key_id in key_ids:
                record = self._keys_by_id.get(key_id)
                if record is not None:
                    result.append(self._make_key_info(record))
            return result

    def _validate_key(self, key_secret: str) -> _KeyRecord:
        key_hash = hash_key_secret(key_secret)
        key_id = self._keys_by_hash.get(key_hash)
        if key_id is None:
            raise InvalidAPIKeyError("invalid api key")
        record = self._keys_by_id[key_id]
        if record.key.revoked:
            raise APIKeyRevokedError(
                f"api key has been revoked: {record.key.key_id}"
            )
        return record

    def _record_usage(self, record: _KeyRecord) -> None:
        now = self._clock.now()
        record.total_uses += 1
        record.last_used_at = now
        record.usage_window.record(now)

    def verify_key(self, key_secret: str) -> APIKeyInfo:
        if not key_secret:
            raise ValueError("key_secret cannot be empty")

        with self._lock:
            record = self._validate_key(key_secret)
            self._record_usage(record)
            return self._make_key_info(record)

    def check_permission(self, key_secret: str, required_scope: str) -> bool:
        if not key_secret:
            raise ValueError("key_secret cannot be empty")
        if not required_scope:
            raise ValueError("required_scope cannot be empty")

        with self._lock:
            record = self._validate_key(key_secret)
            return self._scope_registry.has_scope(
                set(record.key.scopes), required_scope
            )

    def require_permission(self, key_secret: str, required_scope: str) -> APIKeyInfo:
        if not key_secret:
            raise ValueError("key_secret cannot be empty")
        if not required_scope:
            raise ValueError("required_scope cannot be empty")

        with self._lock:
            record = self._validate_key(key_secret)
            if not self._scope_registry.has_scope(
                set(record.key.scopes), required_scope
            ):
                raise APIKeyPermissionDeniedError(
                    f"insufficient permissions: requires '{required_scope}'"
                )
            return self._make_key_info(record)

    def revoke_key(self, key_id: str) -> bool:
        if not key_id:
            raise ValueError("key_id cannot be empty")

        with self._lock:
            record = self._keys_by_id.get(key_id)
            if record is None:
                return False
            if record.key.revoked:
                return False

            record.key.revoked = True
            record.key.revoked_at = self._clock.now()
            return True

    def revoke_keys_by_subject(self, subject: str) -> int:
        if not subject:
            raise ValueError("subject cannot be empty")

        with self._lock:
            key_ids = self._keys_by_subject.get(subject, set())
            count = 0
            for key_id in key_ids:
                record = self._keys_by_id.get(key_id)
                if record and not record.key.revoked:
                    record.key.revoked = True
                    record.key.revoked_at = self._clock.now()
                    count += 1
            return count

    def get_usage_stats(self, key_id: str) -> UsageStats:
        if not key_id:
            raise ValueError("key_id cannot be empty")

        with self._lock:
            record = self._keys_by_id.get(key_id)
            if record is None:
                raise APIKeyNotFoundError(f"key not found: {key_id}")
            return self._make_usage_stats(record)

    def get_subject_usage_stats(self, subject: str) -> List[Tuple[str, UsageStats]]:
        if not subject:
            raise ValueError("subject cannot be empty")

        with self._lock:
            key_ids = self._keys_by_subject.get(subject, set())
            result = []
            for key_id in key_ids:
                record = self._keys_by_id.get(key_id)
                if record is not None:
                    result.append((key_id, self._make_usage_stats(record)))
            return result

    def list_keys_by_usage(
        self,
        subject: Optional[str] = None,
        descending: bool = True,
        limit: Optional[int] = None,
    ) -> List[APIKeyInfo]:
        with self._lock:
            if subject:
                key_ids = self._keys_by_subject.get(subject, set())
            else:
                key_ids = set(self._keys_by_id.keys())

            records = []
            for key_id in key_ids:
                record = self._keys_by_id.get(key_id)
                if record is not None:
                    records.append(record)

            now = self._clock.now()
            records.sort(
                key=lambda r: r.usage_window.count(now),
                reverse=descending,
            )

            if limit is not None:
                records = records[:limit]

            return [self._make_key_info(r) for r in records]

    def list_idle_keys(
        self,
        idle_days: Optional[float] = None,
        subject: Optional[str] = None,
    ) -> List[APIKeyInfo]:
        threshold_days = idle_days if idle_days is not None else self._idle_threshold_days
        if threshold_days <= 0:
            raise ValueError("idle_days must be positive")

        with self._lock:
            if subject:
                key_ids = self._keys_by_subject.get(subject, set())
            else:
                key_ids = set(self._keys_by_id.keys())

            now = self._clock.now()
            threshold_seconds = threshold_days * 86400.0
            result = []

            for key_id in key_ids:
                record = self._keys_by_id.get(key_id)
                if record is None:
                    continue
                if record.key.revoked:
                    continue
                last_used = record.last_used_at or record.key.created_at
                idle_seconds = now - last_used
                if idle_seconds >= threshold_seconds:
                    result.append(self._make_key_info(record))

            return result

    def _make_key_info(self, record: _KeyRecord) -> APIKeyInfo:
        return APIKeyInfo(
            key_id=record.key.key_id,
            subject=record.key.subject,
            scopes=record.key.scopes,
            prefix=record.key.prefix,
            created_at=record.key.created_at,
            revoked=record.key.revoked,
            revoked_at=record.key.revoked_at,
            usage=self._make_usage_stats(record),
        )

    def _make_usage_stats(self, record: _KeyRecord) -> UsageStats:
        now = self._clock.now()
        last_used = record.last_used_at
        if last_used is not None:
            idle_seconds = now - last_used
            idle_days = idle_seconds / 86400.0
            is_idle = idle_days >= self._idle_threshold_days
        else:
            idle_seconds = now - record.key.created_at
            idle_days = idle_seconds / 86400.0
            is_idle = idle_days >= self._idle_threshold_days

        return UsageStats(
            total_uses=record.total_uses,
            last_used_at=last_used,
            window_uses=record.usage_window.count(now),
            is_idle=is_idle,
            idle_days=idle_days,
        )

    def clear(self) -> None:
        with self._lock:
            self._keys_by_id.clear()
            self._keys_by_hash.clear()
            self._keys_by_subject.clear()
            self._prefix_index.clear()
