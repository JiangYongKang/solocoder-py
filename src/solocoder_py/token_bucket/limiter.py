from __future__ import annotations

import threading
from typing import Dict

from ..ratelimiter.clock import Clock, SystemClock
from .models import (
    InvalidBucketConfigError,
    NotEnoughTokensError,
    TokenBucketConfig,
    TokenBucketState,
    scaled_to_tokens,
    tokens_to_scaled,
)


class TokenBucket:
    def __init__(
        self,
        capacity: int,
        refill_rate_per_second: float,
        clock: Clock | None = None,
    ) -> None:
        self._config = TokenBucketConfig(
            capacity=capacity,
            refill_rate_per_second=refill_rate_per_second,
        )
        self._clock: Clock = clock or SystemClock()
        self._lock: threading.Lock = threading.Lock()
        self._state = TokenBucketState(
            current_tokens_scaled=self._config.capacity_scaled,
            last_refill_time=self._clock.now(),
        )

    @property
    def capacity(self) -> int:
        return self._config.capacity

    @property
    def refill_rate_per_second(self) -> float:
        return self._config.refill_rate_per_second

    def _refill(self, current_time: float) -> None:
        elapsed = current_time - self._state.last_refill_time
        if elapsed <= 0:
            return
        new_tokens_scaled = int(round(elapsed * self._config.refill_rate_scaled_per_second))
        if new_tokens_scaled <= 0:
            return
        self._state.current_tokens_scaled = min(
            self._state.current_tokens_scaled + new_tokens_scaled,
            self._config.capacity_scaled,
        )
        self._state.last_refill_time = current_time

    def try_acquire(self, tokens: int = 1) -> bool:
        if tokens <= 0:
            raise InvalidBucketConfigError("tokens must be positive")
        with self._lock:
            current_time = self._clock.now()
            self._refill(current_time)
            requested_scaled = tokens_to_scaled(tokens)
            if self._state.current_tokens_scaled >= requested_scaled:
                self._state.current_tokens_scaled -= requested_scaled
                return True
            return False

    def acquire(self, tokens: int = 1) -> None:
        if not self.try_acquire(tokens):
            available = self.get_available_tokens()
            raise NotEnoughTokensError(requested=tokens, available=available)

    def can_acquire(self, tokens: int = 1) -> bool:
        if tokens <= 0:
            raise InvalidBucketConfigError("tokens must be positive")
        with self._lock:
            current_time = self._clock.now()
            self._refill(current_time)
            requested_scaled = tokens_to_scaled(tokens)
            return self._state.current_tokens_scaled >= requested_scaled

    def get_available_tokens(self) -> float:
        with self._lock:
            current_time = self._clock.now()
            self._refill(current_time)
            return scaled_to_tokens(self._state.current_tokens_scaled)


class MultiSubjectTokenBucketLimiter:
    def __init__(
        self,
        capacity: int,
        refill_rate_per_second: float,
        clock: Clock | None = None,
    ) -> None:
        self._global_config = TokenBucketConfig(
            capacity=capacity,
            refill_rate_per_second=refill_rate_per_second,
        )
        self._clock: Clock = clock or SystemClock()
        self._buckets: Dict[str, TokenBucket] = {}
        self._subject_locks: Dict[str, threading.Lock] = {}
        self._struct_lock: threading.Lock = threading.Lock()

    @property
    def default_capacity(self) -> int:
        return self._global_config.capacity

    @property
    def default_refill_rate_per_second(self) -> float:
        return self._global_config.refill_rate_per_second

    def _get_subject_lock(self, subject_id: str) -> threading.Lock:
        with self._struct_lock:
            if subject_id not in self._subject_locks:
                self._subject_locks[subject_id] = threading.Lock()
            return self._subject_locks[subject_id]

    def _get_or_create_bucket_locked(self, subject_id: str) -> TokenBucket:
        with self._struct_lock:
            if subject_id not in self._buckets:
                self._buckets[subject_id] = TokenBucket(
                    capacity=self._global_config.capacity,
                    refill_rate_per_second=self._global_config.refill_rate_per_second,
                    clock=self._clock,
                )
            return self._buckets[subject_id]

    def try_acquire(self, subject_id: str, tokens: int = 1) -> bool:
        subject_lock = self._get_subject_lock(subject_id)
        with subject_lock:
            bucket = self._get_or_create_bucket_locked(subject_id)
            return bucket.try_acquire(tokens)

    def acquire(self, subject_id: str, tokens: int = 1) -> None:
        subject_lock = self._get_subject_lock(subject_id)
        with subject_lock:
            bucket = self._get_or_create_bucket_locked(subject_id)
            bucket.acquire(tokens)

    def can_acquire(self, subject_id: str, tokens: int = 1) -> bool:
        subject_lock = self._get_subject_lock(subject_id)
        with subject_lock:
            bucket = self._get_or_create_bucket_locked(subject_id)
            return bucket.can_acquire(tokens)

    def get_available_tokens(self, subject_id: str) -> float:
        subject_lock = self._get_subject_lock(subject_id)
        with subject_lock:
            bucket = self._get_or_create_bucket_locked(subject_id)
            return bucket.get_available_tokens()

    def has_subject(self, subject_id: str) -> bool:
        with self._struct_lock:
            return subject_id in self._buckets

    def list_subjects(self) -> list[str]:
        with self._struct_lock:
            return list(self._buckets.keys())
