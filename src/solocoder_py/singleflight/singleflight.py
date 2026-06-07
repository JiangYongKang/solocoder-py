from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .clock import Clock, SystemClock
from .models import CallCancelledError, KeyStats, WaitTimeoutError, _Call


@dataclass
class SingleFlight:
    clock: Clock = field(default_factory=SystemClock)
    _calls: Dict[str, _Call] = field(default_factory=dict)
    _stats: Dict[str, KeyStats] = field(default_factory=dict)
    _mu: threading.Lock = field(default_factory=threading.Lock)

    def _get_or_create_stats(self, key: str) -> KeyStats:
        if key not in self._stats:
            self._stats[key] = KeyStats(key=key)
        return self._stats[key]

    def do(
        self,
        key: str,
        fn: Callable[[], Any],
        timeout: Optional[float] = None,
    ) -> Any:
        if not key:
            raise ValueError("key cannot be empty")
        if not callable(fn):
            raise ValueError("fn must be callable")
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be positive")

        with self._mu:
            call = self._calls.get(key)
            if call is None:
                call = _Call(key=key, waiters=0)
                self._calls[key] = call
                is_leader = True
            else:
                call.waiters += 1
                is_leader = False

        if is_leader:
            leader_error: Optional[Exception] = None
            leader_result: Any = None
            try:
                try:
                    leader_result = fn()
                    with self._mu:
                        call.result = leader_result
                        call.error = None
                        call.done = True
                        stats = self._get_or_create_stats(key)
                        stats.executions += 1
                        stats.shared_hits += call.waiters
                        self._calls.pop(key, None)
                        call.event.set()
                except Exception as e:
                    leader_error = e
                    with self._mu:
                        call.result = None
                        call.error = e
                        call.done = True
                        stats = self._get_or_create_stats(key)
                        stats.executions += 1
                        stats.shared_hits += call.waiters
                        stats.failures += 1
                        self._calls.pop(key, None)
                        call.event.set()
            except BaseException as be:
                with self._mu:
                    call.done = True
                    call.error = CallCancelledError(
                        f"Call for key '{key}' cancelled: leader received {type(be).__name__}"
                    )
                    self._calls.pop(key, None)
                    call.event.set()
                raise
            if leader_error is not None:
                raise leader_error
            return leader_result
        else:
            deadline: Optional[float] = None
            if timeout is not None:
                deadline = self.clock.now() + timeout

            while True:
                remaining: Optional[float] = None
                if deadline is not None:
                    remaining = deadline - self.clock.now()
                    if remaining <= 0:
                        with self._mu:
                            if not call.done:
                                call.waiters = max(0, call.waiters - 1)
                        raise WaitTimeoutError(
                            f"Timed out waiting for key '{key}'"
                        )

                finished = call.event.wait(timeout=remaining)

                with self._mu:
                    if call.done:
                        if call.error is not None:
                            raise call.error
                        return call.result
                if not finished:
                    with self._mu:
                        if not call.done:
                            call.waiters = max(0, call.waiters - 1)
                    raise WaitTimeoutError(
                        f"Timed out waiting for key '{key}'"
                    )

    def get_stats(self, key: str) -> Optional[KeyStats]:
        if not key:
            raise ValueError("key cannot be empty")
        with self._mu:
            stats = self._stats.get(key)
            if stats is None:
                return None
            return KeyStats(
                key=stats.key,
                executions=stats.executions,
                shared_hits=stats.shared_hits,
                failures=stats.failures,
            )

    def get_all_stats(self) -> Dict[str, KeyStats]:
        with self._mu:
            return {
                k: KeyStats(
                    key=v.key,
                    executions=v.executions,
                    shared_hits=v.shared_hits,
                    failures=v.failures,
                )
                for k, v in self._stats.items()
            }

    def reset_stats(self) -> None:
        with self._mu:
            self._stats.clear()

    def in_flight_count(self, key: Optional[str] = None) -> int:
        with self._mu:
            if key is not None:
                call = self._calls.get(key)
                if call is None:
                    return 0
                return 1 + call.waiters
            total = 0
            for c in self._calls.values():
                total += 1 + c.waiters
            return total

    def clear(self) -> None:
        with self._mu:
            self._calls.clear()
            self._stats.clear()
