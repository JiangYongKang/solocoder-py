from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .exceptions import InvalidExchangeRateError


class RoundingMode(str, Enum):
    HALF_UP = "half_up"
    FLOOR = "floor"
    CEILING = "ceiling"


@dataclass(frozen=True)
class ExchangeRate:
    base_currency: str
    target_currency: str
    rate: float
    version: int

    def __post_init__(self) -> None:
        if not self.base_currency:
            raise InvalidExchangeRateError("base_currency cannot be empty")
        if not self.target_currency:
            raise InvalidExchangeRateError("target_currency cannot be empty")
        if self.base_currency == self.target_currency:
            raise InvalidExchangeRateError(
                "base_currency and target_currency cannot be the same"
            )
        if self.rate <= 0:
            raise InvalidExchangeRateError("rate must be positive")
        if self.version <= 0:
            raise InvalidExchangeRateError("version must be positive")


@dataclass
class CurrencyPrecision:
    currency: str
    decimal_places: int

    def __post_init__(self) -> None:
        if not self.currency:
            raise ValueError("currency cannot be empty")
        if self.decimal_places < 0:
            raise ValueError("decimal_places cannot be negative")


@dataclass
class ConversionPath:
    path: Tuple[str, ...]
    rates: Tuple[ExchangeRate, ...]

    @property
    def length(self) -> int:
        return len(self.rates)

    @property
    def hops(self) -> int:
        return len(self.rates)

    def compute_rate(self) -> float:
        result = 1.0
        for r in self.rates:
            result *= r.rate
        return result


@dataclass
class ConversionResult:
    amount: float
    source_currency: str
    target_currency: str
    raw_amount: float
    rounded_amount: float
    rounding_loss: float
    path: ConversionPath
    rounding_mode: RoundingMode
    target_decimal_places: int
    version: Optional[int] = None
