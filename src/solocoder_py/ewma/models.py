from dataclasses import dataclass
from typing import Optional


class EWMAError(Exception):
    pass


class InvalidAlphaError(EWMAError):
    def __init__(self, alpha: float, message: Optional[str] = None):
        self.alpha = alpha
        if message is None:
            message = f"Invalid alpha: {alpha}. Alpha must be in (0, 1]."
        super().__init__(message)


class InvalidWarmupError(EWMAError):
    def __init__(self, warmup_period: int, message: Optional[str] = None):
        self.warmup_period = warmup_period
        if message is None:
            message = (
                f"Invalid warmup_period: {warmup_period}. "
                f"Warmup period must be a non-negative integer."
            )
        super().__init__(message)


class InfinityEncounteredError(EWMAError):
    def __init__(self, value: float, message: Optional[str] = None):
        self.value = value
        if message is None:
            message = (
                f"Infinity encountered: {value}. "
                f"EWMA state is contaminated, call reset() to recover."
            )
        super().__init__(message)


@dataclass(frozen=True)
class EWMAResult:
    value: Optional[float]
    corrected_value: Optional[float]
    count: int
    alpha: float
    in_warmup: bool
    contaminated: bool
