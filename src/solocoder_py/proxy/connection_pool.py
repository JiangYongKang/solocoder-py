from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .clock import Clock, SystemClock
from .exceptions import ConnectionPoolError
from .models import ConnectionInfo, ConnectionStatus, ProxyConfig


@dataclass
class PooledConnection:
    id: str
    upstream_address: str
    status: ConnectionStatus
    created_at: float
    last_used_at: float
    reuse_count: int = 0
    closed: bool = False

    def acquire(self) -> None:
        if self.closed:
            raise ConnectionPoolError("Connection is closed")
        if self.status == ConnectionStatus.IN_USE:
            raise ConnectionPoolError("Connection is already in use")
        self.status = ConnectionStatus.IN_USE
        self.reuse_count += 1

    def release(self, now: float) -> None:
        if self.closed:
            return
        self.status = ConnectionStatus.IDLE
        self.last_used_at = now

    def close(self) -> None:
        self.closed = True
        self.status = ConnectionStatus.CLOSED

    def should_expire(self, now: float, max_idle_time: float) -> bool:
        if self.closed:
            return True
        if self.status == ConnectionStatus.IN_USE:
            return False
        return (now - self.last_used_at) >= max_idle_time

    def should_rotate(self, max_reuse_count: int) -> bool:
        return self.reuse_count >= max_reuse_count

    def get_info(self) -> ConnectionInfo:
        return ConnectionInfo(
            id=self.id,
            upstream_address=self.upstream_address,
            status=self.status,
            created_at=self.created_at,
            last_used_at=self.last_used_at,
            reuse_count=self.reuse_count,
        )


class ConnectionPool:
    def __init__(
        self,
        config: Optional[ProxyConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config = config or ProxyConfig()
        self._clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._connections: Dict[str, Dict[str, PooledConnection]] = {}
        self._connection_counter = 0

    def _get_or_create_pool(self, upstream_address: str) -> Dict[str, PooledConnection]:
        if upstream_address not in self._connections:
            self._connections[upstream_address] = {}
        return self._connections[upstream_address]

    def _cleanup_expired(self) -> None:
        now = self._clock.now()
        for upstream_address in list(self._connections.keys()):
            pool = self._connections[upstream_address]
            for conn_id in list(pool.keys()):
                conn = pool[conn_id]
                if conn.should_expire(now, self._config.max_idle_time):
                    conn.close()
                    del pool[conn_id]
            if not pool:
                del self._connections[upstream_address]

    def acquire(self, upstream_address: str) -> PooledConnection:
        with self._lock:
            self._cleanup_expired()
            pool = self._get_or_create_pool(upstream_address)

            for conn in pool.values():
                if conn.status == ConnectionStatus.IDLE and not conn.should_rotate(
                    self._config.max_reuse_count
                ):
                    conn.acquire()
                    result = conn
                    break
            else:
                if len(pool) >= self._config.max_pool_size:
                    for conn in pool.values():
                        if conn.status == ConnectionStatus.IDLE:
                            conn.close()
                            del pool[conn.id]
                            break
                    if len(pool) >= self._config.max_pool_size:
                        raise ConnectionPoolError(
                            f"Connection pool for {upstream_address} is full"
                        )

                now = self._clock.now()
                conn_id = f"{upstream_address}-{uuid.uuid4().hex[:8]}"
                new_conn = PooledConnection(
                    id=conn_id,
                    upstream_address=upstream_address,
                    status=ConnectionStatus.IDLE,
                    created_at=now,
                    last_used_at=now,
                )
                new_conn.acquire()
                pool[conn_id] = new_conn
                result = new_conn

            self._connection_counter += 1
            return result

    def release(self, conn: PooledConnection) -> None:
        with self._lock:
            now = self._clock.now()
            if conn.should_rotate(self._config.max_reuse_count):
                conn.close()
                pool = self._connections.get(conn.upstream_address, {})
                if conn.id in pool:
                    del pool[conn.id]
            else:
                conn.release(now)
            self._cleanup_expired()

    def invalidate(self, conn: PooledConnection) -> None:
        with self._lock:
            conn.close()
            pool = self._connections.get(conn.upstream_address, {})
            if conn.id in pool:
                del pool[conn.id]
            self._cleanup_expired()

    def get_pool_size(self, upstream_address: str) -> int:
        with self._lock:
            pool = self._connections.get(upstream_address, {})
            return len([c for c in pool.values() if not c.closed])

    def get_total_connections(self) -> int:
        with self._lock:
            total = 0
            for pool in self._connections.values():
                total += len([c for c in pool.values() if not c.closed])
            return total

    def get_active_connections(self) -> int:
        with self._lock:
            total = 0
            for pool in self._connections.values():
                total += len(
                    [c for c in pool.values() if c.status == ConnectionStatus.IN_USE]
                )
            return total

    def get_connection_info(self, upstream_address: Optional[str] = None) -> List[ConnectionInfo]:
        with self._lock:
            infos: List[ConnectionInfo] = []
            if upstream_address:
                pool = self._connections.get(upstream_address, {})
                infos = [c.get_info() for c in pool.values() if not c.closed]
            else:
                for pool in self._connections.values():
                    infos.extend([c.get_info() for c in pool.values() if not c.closed])
            return infos

    def close_all(self) -> None:
        with self._lock:
            for pool in self._connections.values():
                for conn in pool.values():
                    conn.close()
            self._connections.clear()

    @property
    def connection_counter(self) -> int:
        return self._connection_counter
