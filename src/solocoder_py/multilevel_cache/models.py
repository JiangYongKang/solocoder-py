from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar


K = TypeVar("K")
V = TypeVar("V")


class DataSource(Protocol[K, V]):
    def load(self, key: K) -> V: ...


@dataclass(frozen=True)
class CacheStats:
    l1_hits: int = 0
    l2_hits: int = 0
    l1_misses: int = 0
    l2_misses: int = 0
    data_source_loads: int = 0
    evictions_l1: int = 0
    evictions_l2: int = 0
