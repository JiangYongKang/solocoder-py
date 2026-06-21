import math
from typing import Optional

from .models import (
    EWMAError,
    InvalidAlphaError,
    InvalidWarmupError,
    InfinityEncounteredError,
    EWMAResult,
)


class EWMA:
    def __init__(
        self,
        alpha: float,
        warmup_period: int = 0,
        initial_value: Optional[float] = None,
    ) -> None:
        self._validate_alpha(alpha)
        self._validate_warmup_period(warmup_period)

        self._alpha: float = float(alpha)
        self._warmup_period: int = int(warmup_period)
        self._initial_value: Optional[float] = float(initial_value) if initial_value is not None else None

        self._s: float = self._initial_value if self._initial_value is not None else 0.0
        self._count: int = 0
        self._last_valid: Optional[float] = None
        self._contaminated: bool = False
        self._correction_factor_power: float = 1.0

    @staticmethod
    def _validate_alpha(alpha: float) -> None:
        if isinstance(alpha, bool):
            raise InvalidAlphaError(alpha)
        if not isinstance(alpha, (int, float)):
            raise InvalidAlphaError(alpha)
        a = float(alpha)
        if math.isnan(a) or math.isinf(a):
            raise InvalidAlphaError(a)
        if a <= 0.0 or a > 1.0:
            raise InvalidAlphaError(a)

    @staticmethod
    def _validate_warmup_period(warmup_period: int) -> None:
        if isinstance(warmup_period, bool):
            raise InvalidWarmupError(warmup_period)
        if not isinstance(warmup_period, int):
            raise InvalidWarmupError(warmup_period)
        if warmup_period < 0:
            raise InvalidWarmupError(warmup_period)

    @staticmethod
    def _validate_input(value: float) -> str:
        if isinstance(value, bool):
            raise EWMAError(f"Invalid input type: bool is not allowed, use int or float")
        if not isinstance(value, (int, float)):
            raise EWMAError(f"Invalid input type: {type(value)}")
        v = float(value)
        if math.isnan(v):
            return "nan"
        if math.isinf(v):
            return "inf"
        return "valid"

    def update(self, value: float) -> Optional[float]:
        if self._contaminated:
            raise InfinityEncounteredError(float("inf"))

        status = self._validate_input(value)

        if status == "nan":
            return self.value

        if status == "inf":
            self._contaminated = True
            raise InfinityEncounteredError(float(value))

        x = float(value)
        self._count += 1

        if self._count == 1 and self._initial_value is None:
            self._s = x
        else:
            self._s = self._alpha * x + (1.0 - self._alpha) * self._s

        self._correction_factor_power *= 1.0 - self._alpha
        self._last_valid = x

        return self.value

    def update_all(self, values) -> Optional[float]:
        result = None
        for v in values:
            result = self.update(v)
        return result

    def reset(self) -> None:
        self._s = self._initial_value if self._initial_value is not None else 0.0
        self._count = 0
        self._last_valid = None
        self._contaminated = False
        self._correction_factor_power = 1.0

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def warmup_period(self) -> int:
        return self._warmup_period

    @property
    def count(self) -> int:
        return self._count

    @property
    def contaminated(self) -> bool:
        return self._contaminated

    @property
    def in_warmup(self) -> bool:
        if self._warmup_period == 0:
            return False
        if self._count == 0:
            return False
        return self._count <= self._warmup_period

    @property
    def raw_value(self) -> Optional[float]:
        if self._count == 0 and self._initial_value is None:
            return None
        return self._s

    def _compute_corrected(self) -> float:
        correction = 1.0 - self._correction_factor_power
        if correction == 0.0:
            return self._s
        if self._initial_value is None:
            return self._s / correction
        data_weighted_sum = self._s - self._correction_factor_power * self._initial_value
        return data_weighted_sum / correction

    @property
    def value(self) -> Optional[float]:
        if self._contaminated:
            return None
        if self._count == 0 and self._initial_value is None:
            return None

        if self._initial_value is None and self.in_warmup:
            return self._compute_corrected()

        return self._s

    @property
    def corrected_value(self) -> Optional[float]:
        if self._contaminated:
            return None
        if self._count == 0 and self._initial_value is None:
            return None

        if self._warmup_period > 0:
            return self._compute_corrected()

        return self._s

    @property
    def last_valid(self) -> Optional[float]:
        return self._last_valid

    def get_result(self) -> EWMAResult:
        return EWMAResult(
            value=self.value,
            corrected_value=self.corrected_value,
            count=self._count,
            alpha=self._alpha,
            in_warmup=self.in_warmup,
            contaminated=self._contaminated,
        )

    def copy(self) -> "EWMA":
        new = EWMA.__new__(EWMA)
        new._alpha = self._alpha
        new._warmup_period = self._warmup_period
        new._initial_value = self._initial_value
        new._s = self._s
        new._count = self._count
        new._last_valid = self._last_valid
        new._contaminated = self._contaminated
        new._correction_factor_power = self._correction_factor_power
        return new

    def __repr__(self) -> str:
        return (
            f"EWMA(alpha={self._alpha}, warmup_period={self._warmup_period}, "
            f"count={self._count}, value={self.value}, "
            f"in_warmup={self.in_warmup}, contaminated={self._contaminated})"
        )
