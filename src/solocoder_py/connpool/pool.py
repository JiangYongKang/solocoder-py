from __future__ import annotations

import threading
import warnings
from typing import Deque, Optional, Set
from collections import deque

from .clock import Clock, RealClock
from .connection import MockTCPConnection
from .exceptions import (
    ConnectionNotFoundError,
    HealthCheckFailedError,
    PoolClosedError,
    PoolExhaustedError,
)
from .models import ConnectionState, PoolConfig, PoolStats, PoolWaitStrategy


class ConnectionPool:
    def __init__(
        self,
        host: str,
        port: int,
        config: Optional[PoolConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._host: str = host
        self._port: int = port
        self._config: PoolConfig = config if config is not None else PoolConfig()
        self._clock: Clock = clock if clock is not None else RealClock()

        if self._config.max_size < 0:
            raise ValueError("max_size cannot be negative")

        self._lock: threading.Lock = threading.Lock()
        self._not_empty: threading.Condition = threading.Condition(self._lock)

        self._idle_conns: Deque[MockTCPConnection] = deque()
        self._borrowed_conns: Set[MockTCPConnection] = set()
        self._all_conns: Set[MockTCPConnection] = set()

        self._closed: bool = False
        self._eviction_thread: Optional[threading.Thread] = None
        self._eviction_stop_event: threading.Event = threading.Event()

        self._stats: PoolStats = PoolStats()

        if self._config.eviction_interval > 0:
            self._start_eviction_thread()

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def config(self) -> PoolConfig:
        return self._config

    @property
    def stats(self) -> PoolStats:
        with self._lock:
            return PoolStats(
                total_connections=self._stats.total_connections,
                idle_connections=len(self._idle_conns),
                borrowed_connections=len(self._borrowed_conns),
                closed_connections=self._stats.closed_connections,
                borrow_count=self._stats.borrow_count,
                return_count=self._stats.return_count,
                evicted_count=self._stats.evicted_count,
                health_check_failed_count=self._stats.health_check_failed_count,
                health_check_timeout_count=self._stats.health_check_timeout_count,
                eviction_error_count=self._stats.eviction_error_count,
            )

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def size(self) -> int:
        with self._lock:
            return len(self._idle_conns) + len(self._borrowed_conns)

    def idle_size(self) -> int:
        with self._lock:
            return len(self._idle_conns)

    def borrowed_size(self) -> int:
        with self._lock:
            return len(self._borrowed_conns)

    def borrow(self, timeout: Optional[float] = None) -> MockTCPConnection:
        wait_timeout = timeout if timeout is not None else self._config.wait_timeout
        deadline = None

        while True:
            with self._lock:
                if self._closed:
                    raise PoolClosedError("Connection pool is closed")

                if self._idle_conns:
                    conn = self._idle_conns.popleft()
                    self._all_conns.discard(conn)
                else:
                    conn = None

                if conn is None:
                    if len(self._all_conns) < self._config.max_size:
                        conn = self._create_connection()
                        self._borrowed_conns.add(conn)
                        self._stats.borrow_count += 1
                        conn.state = ConnectionState.BORROWED
                        conn.last_borrowed_at = self._clock.now()
                        conn.borrow_count += 1
                        return conn

                    if self._config.wait_strategy == PoolWaitStrategy.FAIL:
                        raise PoolExhaustedError(
                            f"Pool exhausted, max_size={self._config.max_size}"
                        )

                    if deadline is None:
                        deadline = self._clock.now() + wait_timeout
                    remaining = deadline - self._clock.now()
                    if remaining <= 0:
                        raise PoolExhaustedError(
                            f"Pool exhausted after waiting {wait_timeout}s, "
                            f"max_size={self._config.max_size}"
                        )
                    self._not_empty.wait(timeout=remaining)
                    continue

            if not self._config.health_check_on_borrow:
                with self._lock:
                    self._all_conns.add(conn)
                    self._borrowed_conns.add(conn)
                    self._stats.borrow_count += 1
                    conn.state = ConnectionState.BORROWED
                    conn.last_borrowed_at = self._clock.now()
                    conn.borrow_count += 1
                    return conn

            healthy = False
            timed_out = False
            result_holder: dict = {}

            def check():
                try:
                    result_holder["result"] = conn.health_check(
                        timeout=self._config.health_check_timeout
                    )
                except Exception as e:
                    result_holder["exception"] = e

            t = threading.Thread(target=check, daemon=True)
            t.start()
            t.join(timeout=self._config.health_check_timeout)

            if t.is_alive():
                timed_out = True
            elif "exception" in result_holder:
                healthy = False
            else:
                healthy = result_holder.get("result", False)

            with self._lock:
                if not healthy:
                    if timed_out:
                        self._stats.health_check_timeout_count += 1
                    else:
                        self._stats.health_check_failed_count += 1
                    conn.close()
                    self._stats.closed_connections += 1
                    continue

                self._all_conns.add(conn)
                self._borrowed_conns.add(conn)
                self._stats.borrow_count += 1
                conn.state = ConnectionState.BORROWED
                conn.last_borrowed_at = self._clock.now()
                conn.borrow_count += 1
                return conn

    def _create_connection(self) -> MockTCPConnection:
        now = self._clock.now()
        conn = MockTCPConnection(
            host=self._host,
            port=self._port,
            created_at=now,
            last_idle_start=now,
        )
        conn.connect()
        self._all_conns.add(conn)
        self._stats.total_connections += 1
        return conn

    def _destroy_connection(self, conn: MockTCPConnection) -> None:
        conn.close()
        self._all_conns.discard(conn)
        self._borrowed_conns.discard(conn)
        self._stats.closed_connections += 1

    def return_conn(self, conn: MockTCPConnection) -> None:
        with self._lock:
            if self._closed:
                if conn in self._all_conns:
                    self._destroy_connection(conn)
                return

            if conn not in self._borrowed_conns:
                if conn not in self._all_conns:
                    raise ConnectionNotFoundError(
                        "Connection does not belong to this pool"
                    )
                return

            self._borrowed_conns.remove(conn)
            self._stats.return_count += 1

            if conn.is_closed:
                self._destroy_connection(conn)
                self._not_empty.notify()
                return

            now = self._clock.now()
            age = now - conn.created_at
            if self._config.max_lifetime > 0 and age >= self._config.max_lifetime:
                self._destroy_connection(conn)
                self._not_empty.notify()
                return

            conn.state = ConnectionState.IDLE
            conn.last_idle_start = now
            self._idle_conns.append(conn)
            self._not_empty.notify()

    def _start_eviction_thread(self) -> None:
        self._eviction_thread = threading.Thread(
            target=self._eviction_loop, daemon=True
        )
        self._eviction_thread.start()

    def _eviction_loop(self) -> None:
        while not self._eviction_stop_event.is_set():
            self._eviction_stop_event.wait(self._config.eviction_interval)
            if self._eviction_stop_event.is_set():
                break
            try:
                self._evict_idle_connections()
            except Exception as e:
                with self._lock:
                    self._stats.eviction_error_count += 1
                warnings.warn(
                    f"Eviction error: {e}. Eviction thread will continue running.",
                    RuntimeWarning,
                    stacklevel=2,
                )

    def _evict_idle_connections(self) -> None:
        with self._lock:
            if self._closed:
                return

            now = self._clock.now()
            to_evict: list[MockTCPConnection] = []

            for conn in list(self._idle_conns):
                idle_time = now - conn.last_idle_start
                if idle_time >= self._config.idle_timeout:
                    to_evict.append(conn)

            for conn in to_evict:
                self._idle_conns.remove(conn)
                self._destroy_connection(conn)
                self._stats.evicted_count += 1

    def evict_now(self) -> int:
        self._evict_idle_connections()
        with self._lock:
            return self._stats.evicted_count

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True

            if self._eviction_thread is not None:
                self._eviction_stop_event.set()

            for conn in list(self._idle_conns):
                self._destroy_connection(conn)
            self._idle_conns.clear()

            for conn in list(self._borrowed_conns):
                self._destroy_connection(conn)
            self._borrowed_conns.clear()

            self._not_empty.notify_all()

        if self._eviction_thread is not None:
            self._eviction_thread.join(timeout=5.0)
            self._eviction_thread = None

    def __enter__(self) -> "ConnectionPool":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
