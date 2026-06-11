from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar


K = TypeVar("K")
V = TypeVar("V")


class _SentinelType:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _SentinelType()


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


class _MutableStats:
    def __init__(self) -> None:
        self.l1_hits: int = 0
        self.l2_hits: int = 0
        self.l1_misses: int = 0
        self.l2_misses: int = 0
        self.data_source_loads: int = 0

    def reset(self) -> None:
        self.l1_hits = 0
        self.l2_hits = 0
        self.l1_misses = 0
        self.l2_misses = 0
        self.data_source_loads = 0
