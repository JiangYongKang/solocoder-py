from __future__ import annotations

import threading
import uuid
from typing import Optional

from .models import PNCounterDiff, PNCounterState


class PNCounter:
    def __init__(self, replica_id: Optional[str] = None) -> None:
        self._replica_id = replica_id or str(uuid.uuid4())
        self._positive: dict[str, int] = {}
        self._negative: dict[str, int] = {}
        self._lock = threading.RLock()

    @property
    def replica_id(self) -> str:
        return self._replica_id

    @classmethod
    def from_state(cls, state: PNCounterState, replica_id: Optional[str] = None) -> "PNCounter":
        obj = cls(replica_id=replica_id)
        with obj._lock:
            obj._positive = dict(state.positive)
            obj._negative = dict(state.negative)
        return obj

    def increment(self, delta: int = 1) -> None:
        if delta < 0:
            raise ValueError("delta must be non-negative for increment; use decrement for negative deltas")
        if delta == 0:
            return
        with self._lock:
            self._positive[self._replica_id] = self._positive.get(self._replica_id, 0) + delta

    def decrement(self, delta: int = 1) -> None:
        if delta < 0:
            raise ValueError("delta must be non-negative for decrement; use increment for positive deltas")
        if delta == 0:
            return
        with self._lock:
            self._negative[self._replica_id] = self._negative.get(self._replica_id, 0) + delta

    def value(self) -> int:
        with self._lock:
            total = sum(self._positive.values()) - sum(self._negative.values())
            return max(total, 0)

    def get_state(self) -> PNCounterState:
        with self._lock:
            return PNCounterState(
                positive=dict(self._positive),
                negative=dict(self._negative),
            )

    def merge(self, other: "PNCounter") -> None:
        if not isinstance(other, PNCounter):
            raise TypeError("can only merge with another PNCounter")
        with self._lock, other._lock:
            other_state = other.get_state()
            for rid, val in other_state.positive.items():
                self._positive[rid] = max(self._positive.get(rid, 0), val)
            for rid, val in other_state.negative.items():
                self._negative[rid] = max(self._negative.get(rid, 0), val)

    def diff(self, other: "PNCounter") -> PNCounterDiff:
        if not isinstance(other, PNCounter):
            raise TypeError("can only compute diff with another PNCounter")
        with self._lock, other._lock:
            self_state = self.get_state()
            other_state = other.get_state()

        added_positive: dict[str, int] = {}
        added_negative: dict[str, int] = {}
        increased_positive: dict[str, tuple[int, int]] = {}
        increased_negative: dict[str, tuple[int, int]] = {}

        for rid, val in self_state.positive.items():
            if rid not in other_state.positive:
                added_positive[rid] = val
            elif val > other_state.positive[rid]:
                increased_positive[rid] = (other_state.positive[rid], val)

        for rid, val in self_state.negative.items():
            if rid not in other_state.negative:
                added_negative[rid] = val
            elif val > other_state.negative[rid]:
                increased_negative[rid] = (other_state.negative[rid], val)

        return PNCounterDiff(
            added_positive=added_positive,
            added_negative=added_negative,
            increased_positive=increased_positive,
            increased_negative=increased_negative,
        )

    def is_ge(self, other: "PNCounter") -> bool:
        if not isinstance(other, PNCounter):
            raise TypeError("can only compare with another PNCounter")
        with self._lock, other._lock:
            self_state = self.get_state()
            other_state = other.get_state()

        for rid, val in other_state.positive.items():
            if self_state.positive.get(rid, 0) < val:
                return False
        for rid, val in other_state.negative.items():
            if self_state.negative.get(rid, 0) < val:
                return False
        return True
