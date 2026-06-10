from __future__ import annotations

import math
from typing import Optional

from .exceptions import EmptyDigestError, InvalidQuantileError
from .models import Centroid


class TDigest:
    def __init__(self, delta: float = 100.0) -> None:
        if delta <= 0:
            raise ValueError("delta must be positive")
        self._delta = delta
        self._centroids: list[Centroid] = []
        self._total_weight: float = 0.0
        self._buffer: list[Centroid] = []
        self._buffer_size: int = max(int(delta * 2), 50)

    @property
    def delta(self) -> float:
        return self._delta

    @property
    def total_weight(self) -> float:
        self._flush_buffer()
        return self._total_weight

    @property
    def centroids(self) -> list[Centroid]:
        self._flush_buffer()
        return list(self._centroids)

    @property
    def is_empty(self) -> bool:
        self._flush_buffer()
        return self._total_weight == 0.0

    def add(self, value: float, weight: float = 1.0, timestamp: float = 0.0) -> None:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        if weight <= 0:
            raise ValueError("weight must be positive")
        if not math.isfinite(timestamp):
            raise ValueError("timestamp must be finite")

        self._buffer.append(Centroid(mean=value, weight=weight, timestamp=timestamp))
        if len(self._buffer) >= self._buffer_size:
            self._flush_buffer()

    def add_centroid(self, centroid: Centroid) -> None:
        self._buffer.append(Centroid(mean=centroid.mean, weight=centroid.weight, timestamp=centroid.timestamp))
        if len(self._buffer) >= self._buffer_size:
            self._flush_buffer()

    def quantile(self, q: float) -> float:
        if not (0.0 <= q <= 1.0):
            raise InvalidQuantileError(f"Quantile must be in [0, 1], got {q}")
        if self.is_empty:
            raise EmptyDigestError("Digest is empty")

        self._flush_buffer()

        if len(self._centroids) == 1:
            return self._centroids[0].mean

        if q == 0.0:
            return self._centroids[0].mean
        if q == 1.0:
            return self._centroids[-1].mean

        target_weight = q * self._total_weight
        cumulative = 0.0

        for i, c in enumerate(self._centroids):
            if cumulative + c.weight >= target_weight:
                if i == 0:
                    return c.mean
                prev = self._centroids[i - 1]
                prev_cumulative = cumulative
                if c.weight == 0:
                    return c.mean
                frac = (target_weight - prev_cumulative - c.weight / 2) / c.weight
                frac = max(-0.5, min(0.5, frac))
                return prev.mean + (c.mean - prev.mean) * (0.5 + frac)
            cumulative += c.weight

        return self._centroids[-1].mean

    def quantiles(self, quantiles: list[float]) -> list[float]:
        for q in quantiles:
            if not (0.0 <= q <= 1.0):
                raise InvalidQuantileError(f"Quantile must be in [0, 1], got {q}")
        if self.is_empty:
            raise EmptyDigestError("Digest is empty")

        self._flush_buffer()
        return [self.quantile(q) for q in quantiles]

    def trim(self, current_time: float, window_seconds: float, half_life_seconds: Optional[float] = None) -> None:
        all_centroids: list[Centroid] = []
        all_centroids.extend(self._centroids)
        all_centroids.extend(self._buffer)
        self._buffer.clear()

        cutoff_time = current_time - window_seconds
        if half_life_seconds is not None and half_life_seconds > 0:
            decay_lambda = math.log(2) / half_life_seconds
        else:
            decay_lambda = 0.0

        filtered: list[Centroid] = []
        new_total = 0.0

        for c in all_centroids:
            if c.timestamp < cutoff_time:
                continue
            if decay_lambda > 0:
                age = current_time - c.timestamp
                w = c.weight * math.exp(-decay_lambda * age)
                if w <= 1e-12:
                    continue
            else:
                w = c.weight
            filtered.append(Centroid(mean=c.mean, weight=w, timestamp=c.timestamp))
            new_total += w

        self._centroids = filtered
        self._total_weight = new_total

        if len(self._centroids) > 1:
            self._compress()

    def merge(self, other: "TDigest") -> None:
        other._flush_buffer()
        for c in other._centroids:
            self.add_centroid(c)
        self._flush_buffer()

    def _flush_buffer(self) -> None:
        if not self._buffer:
            return

        for c in self._buffer:
            self._centroids.append(c)
            self._total_weight += c.weight
        self._buffer.clear()

        if len(self._centroids) > 1:
            self._compress()

    def _compress(self) -> None:
        if len(self._centroids) <= 1:
            return

        self._centroids.sort(key=lambda c: c.mean)

        if self._total_weight <= 0:
            return

        compressed: list[Centroid] = []
        cumulative = 0.0
        current: Optional[Centroid] = None

        for c in self._centroids:
            if current is None:
                current = Centroid(mean=c.mean, weight=c.weight, timestamp=c.timestamp)
                continue

            q_left = cumulative / self._total_weight
            q_right = (cumulative + current.weight) / self._total_weight
            k_left = self._k(q_left)
            k_right = self._k(q_right)
            k_diff = k_right - k_left

            if k_diff < 1.0:
                k_diff = 1.0

            max_weight = k_diff * self._total_weight / self._delta

            if current.weight + c.weight <= max_weight:
                new_weight = current.weight + c.weight
                if new_weight > 0:
                    new_mean = (current.mean * current.weight + c.mean * c.weight) / new_weight
                else:
                    new_mean = current.mean
                new_timestamp = max(current.timestamp, c.timestamp)
                current = Centroid(mean=new_mean, weight=new_weight, timestamp=new_timestamp)
            else:
                cumulative += current.weight
                compressed.append(current)
                current = Centroid(mean=c.mean, weight=c.weight, timestamp=c.timestamp)

        if current is not None:
            compressed.append(current)

        self._centroids = compressed
        self._total_weight = sum(c.weight for c in compressed)

    def _k(self, q: float) -> float:
        q = max(0.0, min(1.0, q))
        return self._delta * (math.asin(2 * q - 1) + math.pi / 2) / (2 * math.pi)
