from __future__ import annotations

from bisect import bisect_right
from typing import Sequence

from .exceptions import (
    EmptyHistogramError,
    IncompatibleBoundariesError,
    InvalidBoundariesError,
    InvalidQuantileError,
)


class StreamingHistogram:
    def __init__(self, boundaries: Sequence[float]) -> None:
        self._validate_boundaries(boundaries)
        self._boundaries: list[float] = list(boundaries)
        self._bucket_count: int = len(self._boundaries) - 1
        self._counts: list[int] = [0] * (self._bucket_count + 2)

    @staticmethod
    def _validate_boundaries(boundaries: Sequence[float]) -> None:
        if boundaries is None or len(boundaries) < 2:
            raise InvalidBoundariesError(
                "Bucket boundaries must contain at least 2 elements"
            )
        for i in range(1, len(boundaries)):
            if boundaries[i] <= boundaries[i - 1]:
                raise InvalidBoundariesError(
                    "Bucket boundaries must be strictly increasing"
                )

    @property
    def boundaries(self) -> list[float]:
        return list(self._boundaries)

    @property
    def total_count(self) -> int:
        return sum(self._counts)

    @property
    def underflow_count(self) -> int:
        return self._counts[0]

    @property
    def overflow_count(self) -> int:
        return self._counts[-1]

    @property
    def bucket_counts(self) -> list[int]:
        return list(self._counts[1:-1])

    def insert(self, value: float) -> None:
        if value < self._boundaries[0]:
            self._counts[0] += 1
        elif value >= self._boundaries[-1]:
            self._counts[-1] += 1
        else:
            idx = bisect_right(self._boundaries, value) - 1
            self._counts[idx + 1] += 1

    def get_bucket_percentage(self, bucket_index: int) -> float:
        if bucket_index < 0 or bucket_index >= self._bucket_count:
            raise IndexError(
                f"Bucket index {bucket_index} out of range [0, {self._bucket_count})"
            )
        total = self.total_count
        if total == 0:
            return 0.0
        return self._counts[bucket_index + 1] / total * 100.0

    def quantile(self, q: float) -> float:
        if q < 0 or q > 100:
            raise InvalidQuantileError(
                "Quantile must be in the range [0, 100]"
            )
        total = self.total_count
        if total == 0:
            raise EmptyHistogramError(
                "Cannot compute quantile on an empty histogram"
            )
        if q == 0:
            return self._boundaries[0]
        if q == 100:
            return self._boundaries[-1]

        target_rank = q / 100.0 * total

        cumulative = 0.0
        if target_rank < self._counts[0]:
            return self._boundaries[0]
        cumulative += self._counts[0]

        for i in range(self._bucket_count):
            bucket_count = self._counts[i + 1]
            if cumulative <= target_rank < cumulative + bucket_count:
                lower = self._boundaries[i]
                upper = self._boundaries[i + 1]
                if bucket_count == 0:
                    return lower
                offset = target_rank - cumulative
                return lower + (upper - lower) * (offset / bucket_count)
            cumulative += bucket_count

        return self._boundaries[-1]

    def quantiles(self, qs: Sequence[float]) -> list[float]:
        return [self.quantile(q) for q in qs]

    def merge(self, other: "StreamingHistogram") -> "StreamingHistogram":
        if self._boundaries != other._boundaries:
            raise IncompatibleBoundariesError(
                "Cannot merge histograms with different bucket boundaries"
            )
        merged = StreamingHistogram(self._boundaries)
        for i in range(len(self._counts)):
            merged._counts[i] = self._counts[i] + other._counts[i]
        return merged

    def reset(self) -> None:
        for i in range(len(self._counts)):
            self._counts[i] = 0
