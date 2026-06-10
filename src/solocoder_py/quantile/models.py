from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Centroid:
    mean: float
    weight: float
    timestamp: float = 0.0


@dataclass
class QuantileResult:
    quantile: float
    value: float


@dataclass
class WindowConfig:
    window_seconds: float
    half_life_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.half_life_seconds is not None and self.half_life_seconds <= 0:
            raise ValueError("half_life_seconds must be positive if provided")
