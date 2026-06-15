from __future__ import annotations

import math
import threading
import time
from typing import Optional

from ..ratelimiter.clock import Clock, SystemClock
from .models import (
    AcquireResult,
    TokenBucketConfig,
    TokenBucketState,
    TokenExhaustedError,
    WaitTimeoutError,
)


class TokenBucket:
    def __init__(
        self,
        config: TokenBucketConfig,
        clock: Optional[Clock] = None,
    ) -> None:
        config.validate()
        self._config: TokenBucketConfig = config
        self._clock: Clock = clock or SystemClock()
        self._tokens: float = float(
            config.initial_tokens if config.initial_tokens is not None else config.capacity
        )
        self._last_refill_time: float = self._clock.now()
        self._lock: threading.RLock = threading.RLock()

    def _refill(self) -> None:
        current_time = self._clock.now()
        elapsed = current_time - self._last_refill_time
        if elapsed <= 0:
            return

        tokens_to_add = elapsed * self._config.refill_rate
        self._tokens = min(self._config.capacity, self._tokens + tokens_to_add)
        self._last_refill_time = current_time

    @property
    def capacity(self) -> int:
        with self._lock:
            return self._config.capacity

    @property
    def refill_rate(self) -> float:
        with self._lock:
            return self._config.refill_rate

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    @property
    def last_refill_time(self) -> float:
        with self._lock:
            return self._last_refill_time

    def get_state(self) -> TokenBucketState:
        with self._lock:
            self._refill()
            return TokenBucketState(
                capacity=self._config.capacity,
                refill_rate=self._config.refill_rate,
                tokens=self._tokens,
                last_refill_time=self._last_refill_time,
            )

    def available_tokens(self) -> int:
        with self._lock:
            self._refill()
            return int(math.floor(self._tokens))

    def is_full(self) -> bool:
        with self._lock:
            self._refill()
            return self._tokens >= self._config.capacity

    def is_empty(self) -> bool:
        with self._lock:
            self._refill()
            return self._tokens < 1.0

    def estimated_wait_time(self, tokens_needed: int = 1) -> float:
        if tokens_needed <= 0:
            return 0.0
        with self._lock:
            self._refill()
            if self._tokens >= tokens_needed:
                return 0.0
            deficit = tokens_needed - self._tokens
            return deficit / self._config.refill_rate

    def try_acquire(self, tokens: int = 1) -> AcquireResult:
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return AcquireResult(
                    acquired=True,
                    tokens_consumed=tokens,
                    tokens_remaining=int(math.floor(self._tokens)),
                )
            else:
                deficit = tokens - self._tokens
                retry_after = deficit / self._config.refill_rate
                return AcquireResult(
                    acquired=False,
                    tokens_consumed=0,
                    tokens_remaining=int(math.floor(self._tokens)),
                    retry_after=retry_after,
                )

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> AcquireResult:
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        result = self.try_acquire(tokens)
        if result.acquired:
            return result

        if timeout is not None and timeout <= 0:
            raise TokenExhaustedError(retry_after=result.retry_after)

        wait_time = result.retry_after if result.retry_after is not None else 0
        if timeout is not None and wait_time > timeout:
            raise WaitTimeoutError(waited=0.0, timeout=timeout)

        if isinstance(self._clock, SystemClock):
            time.sleep(wait_time)
            return self.try_acquire(tokens)
        else:
            self._clock.advance(wait_time)
            return self.try_acquire(tokens)

    def set_tokens(self, token_count: int) -> None:
        if token_count < 0:
            raise ValueError("token_count must be non-negative")
        with self._lock:
            self._tokens = min(token_count, self._config.capacity)
            self._last_refill_time = self._clock.now()

    def sync_with_server(
        self,
        server_remaining: Optional[int],
        server_reset_time: Optional[float] = None,
    ) -> None:
        with self._lock:
            if server_remaining is not None:
                if server_remaining < 0:
                    server_remaining = 0
                if server_remaining > self._config.capacity:
                    server_remaining = self._config.capacity
                self._tokens = min(self._tokens, float(server_remaining))

            if server_reset_time is not None:
                current_time = self._clock.now()
                if server_reset_time > current_time:
                    pass
                else:
                    self._tokens = self._config.capacity

            self._last_refill_time = self._clock.now()

    def reset(self) -> None:
        with self._lock:
            self._tokens = float(
                self._config.initial_tokens
                if self._config.initial_tokens is not None
                else self._config.capacity
            )
            self._last_refill_time = self._clock.now()
