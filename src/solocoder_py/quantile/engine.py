from __future__ import annotations

import math
import threading
from typing import Optional

from .clock import Clock, SystemClock
from .exceptions import (
    EmptyDigestError,
    InvalidQuantileError,
    InvalidValueError,
    InvalidWindowError,
)
from .models import QuantileResult, WindowConfig
from .tdigest import TDigest


class QuantileEstimator:
    def __init__(
        self,
        delta: float = 100.0,
        window_config: Optional[WindowConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        if delta <= 0:
            raise ValueError("delta must be positive")

        self._delta = delta
        self._window_config = window_config
        self._clock = clock if clock is not None else SystemClock()
        self._lock = threading.RLock()
        self._digest = TDigest(delta=delta)
        self._insert_count = 0

    @property
    def delta(self) -> float:
        return self._delta

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return self._digest.is_empty

    @property
    def insert_count(self) -> int:
        with self._lock:
            return self._insert_count

    @property
    def total_weight(self) -> float:
        with self._lock:
            return self._digest.total_weight

    @property
    def window_config(self) -> Optional[WindowConfig]:
        return self._window_config

    def insert(self, value: float, weight: float = 1.0) -> None:
        if not math.isfinite(value):
            raise InvalidValueError(f"Value must be finite, got {value}")
        if weight <= 0:
            raise InvalidValueError(f"Weight must be positive, got {weight}")
        if not math.isfinite(weight):
            raise InvalidValueError(f"Weight must be finite, got {weight}")

        with self._lock:
            timestamp = self._clock.now()
            self._digest.add(value=value, weight=weight, timestamp=timestamp)
            self._insert_count += 1

    def insert_many(self, values: list[float], weights: Optional[list[float]] = None) -> None:
        if weights is not None and len(values) != len(weights):
            raise InvalidValueError("values and weights must have the same length")

        validated: list[tuple[float, float]] = []
        for i, v in enumerate(values):
            if not math.isfinite(v):
                raise InvalidValueError(f"Value must be finite, got {v} at index {i}")
            w = weights[i] if weights is not None else 1.0
            if not math.isfinite(w) or w <= 0:
                raise InvalidValueError(f"Weight must be finite and positive, got {w} at index {i}")
            validated.append((v, w))

        with self._lock:
            for v, w in validated:
                timestamp = self._clock.now()
                self._digest.add(value=v, weight=w, timestamp=timestamp)
                self._insert_count += 1

    def quantile(self, q: float, window_seconds: Optional[float] = None) -> float:
        if not (0.0 <= q <= 1.0):
            raise InvalidQuantileError(f"Quantile must be in [0, 1], got {q}")

        with self._lock:
            current_time = self._clock.now()
            effective_window = self._resolve_window(window_seconds)
            effective_half_life = self._resolve_half_life()

            working_digest = self._copy_and_trim(current_time, effective_window, effective_half_life)
            return working_digest.quantile(q)

    def quantiles(
        self,
        quantiles: list[float],
        window_seconds: Optional[float] = None,
    ) -> list[QuantileResult]:
        for q in quantiles:
            if not (0.0 <= q <= 1.0):
                raise InvalidQuantileError(f"Quantile must be in [0, 1], got {q}")

        with self._lock:
            current_time = self._clock.now()
            effective_window = self._resolve_window(window_seconds)
            effective_half_life = self._resolve_half_life()

            working_digest = self._copy_and_trim(current_time, effective_window, effective_half_life)
            values = working_digest.quantiles(quantiles)
            return [QuantileResult(quantile=q, value=v) for q, v in zip(quantiles, values)]

    def p50(self, window_seconds: Optional[float] = None) -> float:
        return self.quantile(0.50, window_seconds)

    def p95(self, window_seconds: Optional[float] = None) -> float:
        return self.quantile(0.95, window_seconds)

    def p99(self, window_seconds: Optional[float] = None) -> float:
        return self.quantile(0.99, window_seconds)

    def common_quantiles(self, window_seconds: Optional[float] = None) -> dict[str, float]:
        qs = [0.50, 0.90, 0.95, 0.99, 0.999]
        results = self.quantiles(qs, window_seconds)
        labels = ["p50", "p90", "p95", "p99", "p999"]
        return {label: r.value for label, r in zip(labels, results)}

    def _resolve_window(self, window_seconds: Optional[float]) -> Optional[float]:
        if window_seconds is not None:
            if window_seconds <= 0:
                raise InvalidWindowError(f"window_seconds must be positive, got {window_seconds}")
            return window_seconds
        if self._window_config is not None:
            return self._window_config.window_seconds
        return None

    def _resolve_half_life(self) -> Optional[float]:
        if self._window_config is not None:
            return self._window_config.half_life_seconds
        return None

    def _copy_and_trim(
        self,
        current_time: float,
        window_seconds: Optional[float],
        half_life_seconds: Optional[float],
    ) -> TDigest:
        source_centroids = self._digest.centroids
        if not source_centroids:
            raise EmptyDigestError("Digest is empty")

        working = TDigest(delta=self._delta)
        for c in source_centroids:
            working.add_centroid(c)

        if window_seconds is not None:
            working.trim(current_time, window_seconds, half_life_seconds)

        if working.is_empty:
            raise EmptyDigestError("No data in the specified time window")

        return working
