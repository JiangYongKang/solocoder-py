from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .enums import CredentialVersion
from .exceptions import InvalidTrafficPercentageError, RotationNotFoundError
from .models import TrafficStats


class StableHashBucketer:
    NUM_BUCKETS = 100

    @staticmethod
    def get_bucket(request_key: str) -> int:
        if not request_key:
            raise ValueError("request_key must not be empty")
        hash_bytes = hashlib.md5(request_key.encode("utf-8")).digest()
        bucket = int.from_bytes(hash_bytes[:2], byteorder="big") % StableHashBucketer.NUM_BUCKETS
        return bucket


@dataclass
class _RotationRoutingState:
    old_credential: str
    new_credential: str
    traffic_percentage: int = 0
    stats: TrafficStats = field(default_factory=TrafficStats)


class TrafficRouter:
    def __init__(self) -> None:
        self._rotations: dict[str, _RotationRoutingState] = {}
        self._lock = threading.RLock()

    def register_rotation(
        self,
        rotation_name: str,
        old_credential: str,
        new_credential: str,
    ) -> None:
        if not rotation_name:
            raise ValueError("rotation_name must not be empty")
        if not old_credential:
            raise ValueError("old_credential must not be empty")
        if not new_credential:
            raise ValueError("new_credential must not be empty")
        if old_credential == new_credential:
            raise ValueError("old_credential and new_credential must be different")

        with self._lock:
            if rotation_name in self._rotations:
                raise RotationNotFoundError(f"rotation '{rotation_name}' already registered")
            self._rotations[rotation_name] = _RotationRoutingState(
                old_credential=old_credential,
                new_credential=new_credential,
            )

    def unregister_rotation(self, rotation_name: str) -> None:
        with self._lock:
            self._get_rotation_or_raise(rotation_name)
            del self._rotations[rotation_name]

    def set_traffic_percentage(self, rotation_name: str, percentage: int) -> None:
        if percentage < 0 or percentage > 100:
            raise InvalidTrafficPercentageError(
                "traffic percentage must be between 0 and 100"
            )

        with self._lock:
            state = self._get_rotation_or_raise(rotation_name)
            state.traffic_percentage = percentage

    def get_traffic_percentage(self, rotation_name: str) -> int:
        with self._lock:
            state = self._get_rotation_or_raise(rotation_name)
            return state.traffic_percentage

    def route(
        self,
        rotation_name: str,
        request_key: str,
        force_version: Optional[CredentialVersion] = None,
    ) -> Tuple[str, CredentialVersion]:
        if not rotation_name:
            raise ValueError("rotation_name must not be empty")
        if not request_key:
            raise ValueError("request_key must not be empty")

        with self._lock:
            state = self._get_rotation_or_raise(rotation_name)

            version = force_version
            if version is None:
                bucket = StableHashBucketer.get_bucket(request_key)
                if bucket < state.traffic_percentage:
                    version = CredentialVersion.NEW
                else:
                    version = CredentialVersion.OLD

            state.stats.total_requests += 1
            if version == CredentialVersion.OLD:
                state.stats.old_requests += 1
                return state.old_credential, version
            else:
                state.stats.new_requests += 1
                return state.new_credential, version

    def record_metrics(
        self,
        rotation_name: str,
        version: CredentialVersion,
        is_error: bool = False,
    ) -> None:
        with self._lock:
            state = self._get_rotation_or_raise(rotation_name)

            if version == CredentialVersion.OLD:
                if is_error:
                    state.stats.old_errors += 1
                state.stats.new_consecutive_failures = 0
            else:
                if is_error:
                    state.stats.new_errors += 1
                    state.stats.new_consecutive_failures += 1
                else:
                    state.stats.new_consecutive_failures = 0

    def record_new_metrics(
        self,
        rotation_name: str,
        is_error: bool = False,
    ) -> None:
        self.record_metrics(rotation_name, CredentialVersion.NEW, is_error)

    def record_old_metrics(
        self,
        rotation_name: str,
        is_error: bool = False,
    ) -> None:
        self.record_metrics(rotation_name, CredentialVersion.OLD, is_error)

    def get_stats(self, rotation_name: str) -> TrafficStats:
        with self._lock:
            state = self._get_rotation_or_raise(rotation_name)
            return TrafficStats(
                total_requests=state.stats.total_requests,
                old_requests=state.stats.old_requests,
                new_requests=state.stats.new_requests,
                old_errors=state.stats.old_errors,
                new_errors=state.stats.new_errors,
                new_consecutive_failures=state.stats.new_consecutive_failures,
            )

    def reset_stats(self, rotation_name: str) -> None:
        with self._lock:
            state = self._get_rotation_or_raise(rotation_name)
            state.stats = TrafficStats()

    def _get_rotation_or_raise(self, rotation_name: str) -> _RotationRoutingState:
        if rotation_name not in self._rotations:
            raise RotationNotFoundError(f"rotation '{rotation_name}' not found")
        return self._rotations[rotation_name]
