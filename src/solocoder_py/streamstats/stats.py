import math
from typing import Optional, Iterable

from .models import InvalidValueError, StatsResult, StreamStatsError


class StreamStats:
    def __init__(self):
        self._n: int = 0
        self._mean: float = 0.0
        self._m2: float = 0.0
        self._m3: float = 0.0
        self._m4: float = 0.0

    @staticmethod
    def _validate(value: float) -> None:
        if isinstance(value, bool):
            raise InvalidValueError(value)
        if not isinstance(value, (int, float)):
            raise InvalidValueError(value)
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            raise InvalidValueError(v)

    def add(self, value: float) -> None:
        self._validate(value)
        x = float(value)
        n1 = self._n
        self._n += 1
        n = self._n
        delta = x - self._mean
        delta_n = delta / n
        delta_n2 = delta_n * delta_n
        term1 = delta * delta_n * n1
        self._mean += delta_n
        self._m4 += (
            term1 * delta_n2 * (n * n - 3 * n + 3)
            + 6 * delta_n2 * self._m2
            - 4 * delta_n * self._m3
        )
        self._m3 += term1 * delta_n * (n - 2) - 3 * delta_n * self._m2
        self._m2 += term1

    def add_all(self, values: Iterable[float]) -> None:
        for v in values:
            self.add(v)

    def merge(self, other: "StreamStats") -> "StreamStats":
        if other is None:
            raise StreamStatsError("Cannot merge with None")
        if self._n == 0:
            self._n = other._n
            self._mean = other._mean
            self._m2 = other._m2
            self._m3 = other._m3
            self._m4 = other._m4
            return self
        if other._n == 0:
            return self

        if other._n > self._n:
            na, nb = other._n, self._n
            mean_a, mean_b = other._mean, self._mean
            m2_a, m2_b = other._m2, self._m2
            m3_a, m3_b = other._m3, self._m3
            m4_a, m4_b = other._m4, self._m4
        else:
            na, nb = self._n, other._n
            mean_a, mean_b = self._mean, other._mean
            m2_a, m2_b = self._m2, other._m2
            m3_a, m3_b = self._m3, other._m3
            m4_a, m4_b = self._m4, other._m4

        nc = na + nb
        delta = mean_b - mean_a
        delta2 = delta * delta

        new_mean = mean_a + delta * nb / nc

        m2_correction = delta2 * na * nb / nc
        new_m2 = m2_a + m2_b + m2_correction

        new_m3 = (
            m3_a
            + m3_b
            + delta * m2_correction * (na - nb) / nc
            + 3 * delta * (na * m2_b - nb * m2_a) / nc
        )

        new_m4 = (
            m4_a
            + m4_b
            + delta2 * m2_correction * (na * na - na * nb + nb * nb) / (nc * nc)
            + 6 * delta2 * (na * na * m2_b + nb * nb * m2_a) / (nc * nc)
            + 4 * delta * (na * m3_b - nb * m3_a) / nc
        )

        self._mean = new_mean
        self._m2 = new_m2
        self._m3 = new_m3
        self._m4 = new_m4
        self._n = nc
        return self

    @property
    def count(self) -> int:
        return self._n

    @property
    def mean(self) -> Optional[float]:
        if self._n == 0:
            return None
        return self._mean

    @property
    def variance_population(self) -> Optional[float]:
        if self._n == 0:
            return None
        return self._m2 / self._n

    @property
    def variance_sample(self) -> Optional[float]:
        if self._n < 2:
            return None
        return self._m2 / (self._n - 1)

    @property
    def variance(self) -> Optional[float]:
        return self.variance_sample

    @property
    def stddev_population(self) -> Optional[float]:
        v = self.variance_population
        if v is None:
            return None
        return math.sqrt(v)

    @property
    def stddev_sample(self) -> Optional[float]:
        v = self.variance_sample
        if v is None:
            return None
        return math.sqrt(v)

    @property
    def skewness(self) -> Optional[float]:
        if self._n < 3:
            return None
        if self._m2 <= 0:
            return None
        return math.sqrt(self._n) * self._m3 / (self._m2 ** 1.5)

    @property
    def kurtosis(self) -> Optional[float]:
        if self._n < 4:
            return None
        if self._m2 <= 0:
            return None
        return (self._n * self._m4) / (self._m2 * self._m2) - 3.0

    def get_result(self) -> StatsResult:
        return StatsResult(
            count=self.count,
            mean=self.mean,
            variance=self.variance,
            skewness=self.skewness,
            kurtosis=self.kurtosis,
        )

    def copy(self) -> "StreamStats":
        new = StreamStats()
        new._n = self._n
        new._mean = self._mean
        new._m2 = self._m2
        new._m3 = self._m3
        new._m4 = self._m4
        return new

    def __add__(self, other: "StreamStats") -> "StreamStats":
        result = self.copy()
        result.merge(other)
        return result

    def __iadd__(self, other: "StreamStats") -> "StreamStats":
        self.merge(other)
        return self

    def __repr__(self) -> str:
        return (
            f"StreamStats(n={self._n}, mean={self._mean}, "
            f"m2={self._m2}, m3={self._m3}, m4={self._m4})"
        )
