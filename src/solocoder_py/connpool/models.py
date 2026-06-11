from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PoolWaitStrategy(str, Enum):
    BLOCK = "block"
    FAIL = "fail"


class ConnectionState(str, Enum):
    IDLE = "idle"
    BORROWED = "borrowed"
    CLOSED = "closed"


@dataclass
class PoolStats:
    total_connections: int = 0
    idle_connections: int = 0
    borrowed_connections: int = 0
    closed_connections: int = 0
    borrow_count: int = 0
    return_count: int = 0
    evicted_count: int = 0
    health_check_failed_count: int = 0

    @property
    def active_connections(self) -> int:
        return self.idle_connections + self.borrowed_connections


@dataclass
class PoolConfig:
    max_size: int = 10
    wait_strategy: PoolWaitStrategy = PoolWaitStrategy.BLOCK
    wait_timeout: float = 5.0
    idle_timeout: float = 60.0
    eviction_interval: float = 30.0
    max_lifetime: float = 300.0
    health_check_on_borrow: bool = True
    health_check_timeout: float = 1.0
