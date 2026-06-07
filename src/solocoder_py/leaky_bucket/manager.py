from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..ratelimiter.clock import Clock, SystemClock
from .bucket import LeakyBucket
from .models import (
    BucketConfig,
    BucketRequest,
    EnqueueResult,
    LeakyBucketState,
    OverflowStrategy,
)


class SubjectLeakyBucketManager:
    def __init__(
        self,
        default_config: Optional[BucketConfig] = None,
        default_overflow_strategy: OverflowStrategy = OverflowStrategy.REJECT_NEW,
        clock: Optional[Clock] = None,
    ) -> None:
        self._default_config: Optional[BucketConfig] = default_config
        self._default_overflow_strategy: OverflowStrategy = default_overflow_strategy
        self._clock: Clock = clock or SystemClock()
        self._buckets: Dict[str, LeakyBucket] = {}
        self._bucket_configs: Dict[str, BucketConfig] = {}
        self._bucket_strategies: Dict[str, OverflowStrategy] = {}
        self._lock: threading.RLock = threading.RLock()

    def register_subject(
        self,
        subject_id: str,
        config: BucketConfig,
        overflow_strategy: Optional[OverflowStrategy] = None,
    ) -> None:
        config.validate()
        with self._lock:
            self._bucket_configs[subject_id] = config
            if overflow_strategy is not None:
                self._bucket_strategies[subject_id] = overflow_strategy
            else:
                self._bucket_strategies[subject_id] = self._default_overflow_strategy
            self._buckets[subject_id] = LeakyBucket(
                config=config,
                overflow_strategy=self._bucket_strategies[subject_id],
                clock=self._clock,
            )

    def unregister_subject(self, subject_id: str) -> None:
        with self._lock:
            self._buckets.pop(subject_id, None)
            self._bucket_configs.pop(subject_id, None)
            self._bucket_strategies.pop(subject_id, None)

    def has_subject(self, subject_id: str) -> bool:
        with self._lock:
            return subject_id in self._buckets

    def _get_or_create_bucket(self, subject_id: str) -> LeakyBucket:
        with self._lock:
            if subject_id in self._buckets:
                return self._buckets[subject_id]

            if self._default_config is None:
                raise ValueError(
                    f"Subject '{subject_id}' is not registered and no default config is set"
                )

            self.register_subject(subject_id, self._default_config)
            return self._buckets[subject_id]

    def enqueue(self, subject_id: str, request: BucketRequest) -> EnqueueResult:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.enqueue(request)

    def current_size(self, subject_id: str) -> int:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.current_size()

    def is_empty(self, subject_id: str) -> bool:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.is_empty()

    def is_full(self, subject_id: str) -> bool:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.is_full()

    def get_state(self, subject_id: str) -> LeakyBucketState:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.get_state()

    def get_dropped_count(self, subject_id: str) -> int:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.dropped_count

    def get_processed_count(self, subject_id: str) -> int:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.processed_count

    def peek_next(self, subject_id: str) -> Optional[BucketRequest]:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.peek_next()

    def get_all_pending(self, subject_id: str) -> List[BucketRequest]:
        bucket = self._get_or_create_bucket(subject_id)
        return bucket.get_all_pending()

    def get_all_subject_ids(self) -> List[str]:
        with self._lock:
            return list(self._buckets.keys())

    def clear_subject(self, subject_id: str) -> None:
        bucket = self._get_or_create_bucket(subject_id)
        bucket.clear()

    def reset_subject(self, subject_id: str) -> None:
        bucket = self._get_or_create_bucket(subject_id)
        bucket.reset()

    def clear_all(self) -> None:
        with self._lock:
            for bucket in self._buckets.values():
                bucket.clear()

    def reset_all(self) -> None:
        with self._lock:
            for bucket in self._buckets.values():
                bucket.reset()

    def get_bucket(self, subject_id: str) -> Optional[LeakyBucket]:
        with self._lock:
            return self._buckets.get(subject_id)
