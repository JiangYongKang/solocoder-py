from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from ..ratelimiter.clock import Clock, SystemClock
from .models import (
    AcquireResult,
    InvalidResponseHeaderError,
    RateLimitHeaders,
    RateLimiterError,
    SyncStrategy,
    TokenBucketConfig,
)
from .token_bucket import TokenBucket


class RateLimiter:
    def __init__(
        self,
        config: TokenBucketConfig,
        sync_strategy: SyncStrategy = SyncStrategy.MIN,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config: TokenBucketConfig = config
        self._sync_strategy: SyncStrategy = sync_strategy
        self._clock: Clock = clock or SystemClock()
        self._bucket: TokenBucket = TokenBucket(config=config, clock=self._clock)
        self._last_headers: Optional[RateLimitHeaders] = None
        self._lock: threading.RLock = threading.RLock()

    @property
    def capacity(self) -> int:
        with self._lock:
            return self._bucket.capacity

    @property
    def refill_rate(self) -> float:
        with self._lock:
            return self._bucket.refill_rate

    @property
    def available_tokens(self) -> int:
        with self._lock:
            return self._bucket.available_tokens()

    @property
    def sync_strategy(self) -> SyncStrategy:
        with self._lock:
            return self._sync_strategy

    @sync_strategy.setter
    def sync_strategy(self, strategy: SyncStrategy) -> None:
        with self._lock:
            self._sync_strategy = strategy

    @property
    def last_headers(self) -> Optional[RateLimitHeaders]:
        with self._lock:
            return self._last_headers

    def is_full(self) -> bool:
        with self._lock:
            return self._bucket.is_full()

    def is_empty(self) -> bool:
        with self._lock:
            return self._bucket.is_empty()

    def estimated_wait_time(self, tokens_needed: int = 1) -> float:
        with self._lock:
            return self._bucket.estimated_wait_time(tokens_needed)

    def try_acquire(self, tokens: int = 1) -> AcquireResult:
        with self._lock:
            return self._bucket.try_acquire(tokens)

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> AcquireResult:
        with self._lock:
            return self._bucket.acquire(tokens, timeout)

    def update_from_response_headers(self, headers: Dict[str, Any]) -> None:
        with self._lock:
            try:
                parsed = RateLimitHeaders.from_headers(headers)
            except InvalidResponseHeaderError:
                raise

            self._last_headers = parsed

            server_remaining = parsed.remaining
            server_reset = parsed.reset

            if self._sync_strategy == SyncStrategy.MIN:
                self._bucket.sync_with_server(
                    server_remaining=server_remaining,
                    server_reset_time=server_reset,
                )
            elif self._sync_strategy == SyncStrategy.SERVER:
                if server_remaining is not None:
                    self._bucket.set_tokens(max(0, min(server_remaining, self._bucket.capacity)))
                if server_reset is not None and server_reset <= self._clock.now():
                    self._bucket.set_tokens(self._bucket.capacity)
            elif self._sync_strategy == SyncStrategy.LOCAL:
                pass

    def update_from_headers_object(self, headers: RateLimitHeaders) -> None:
        with self._lock:
            self._last_headers = headers

            server_remaining = headers.remaining
            server_reset = headers.reset

            if self._sync_strategy == SyncStrategy.MIN:
                self._bucket.sync_with_server(
                    server_remaining=server_remaining,
                    server_reset_time=server_reset,
                )
            elif self._sync_strategy == SyncStrategy.SERVER:
                if server_remaining is not None:
                    self._bucket.set_tokens(max(0, min(server_remaining, self._bucket.capacity)))
                if server_reset is not None and server_reset <= self._clock.now():
                    self._bucket.set_tokens(self._bucket.capacity)
            elif self._sync_strategy == SyncStrategy.LOCAL:
                pass

    def reset(self) -> None:
        with self._lock:
            self._bucket.reset()
            self._last_headers = None

    def get_bucket_state(self):
        with self._lock:
            return self._bucket.get_state()
