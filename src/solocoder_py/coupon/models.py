from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from .exceptions import InvalidCouponError


class CouponType(str, Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"
    TIERED = "tiered"


class TierDiscountType(str, Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"


@dataclass
class Tier:
    min_amount: float
    max_amount: Optional[float]
    discount_type: TierDiscountType
    discount_value: float

    def __post_init__(self) -> None:
        if self.min_amount < 0:
            raise InvalidCouponError("Tier min_amount cannot be negative")
        if self.max_amount is not None and self.max_amount <= self.min_amount:
            raise InvalidCouponError("Tier max_amount must be greater than min_amount")
        if self.discount_value <= 0:
            raise InvalidCouponError("Tier discount_value must be positive")
        if self.discount_type == TierDiscountType.PERCENTAGE and self.discount_value > 1:
            raise InvalidCouponError("Percentage tier discount_value must be <= 1")


@dataclass
class Coupon(ABC):
    coupon_id: str
    name: str
    valid_from: datetime
    valid_until: datetime
    mutex_groups: List[str] = field(default_factory=list)
    priority: int = 0
    max_discount: Optional[float] = None

    def __post_init__(self) -> None:
        if self.valid_until <= self.valid_from:
            raise InvalidCouponError("valid_until must be after valid_from")
        if self.max_discount is not None and self.max_discount < 0:
            raise InvalidCouponError("max_discount cannot be negative")

    @property
    @abstractmethod
    def coupon_type(self) -> CouponType:
        ...

    def is_valid_at(self, check_time: datetime) -> bool:
        return self.valid_from <= check_time <= self.valid_until

    @abstractmethod
    def _calculate_raw_discount(self, amount: float) -> float:
        ...

    def calculate_discount(self, amount: float, check_time: datetime) -> tuple[float, bool]:
        if amount < 0:
            raise InvalidCouponError("Order amount cannot be negative")
        raw = self._calculate_raw_discount(amount)
        capped = False
        if self.max_discount is not None and raw >= self.max_discount and raw > 0:
            raw = self.max_discount
            capped = True
        if raw > amount:
            raw = amount
        return max(0.0, raw), capped


@dataclass
class FixedAmountCoupon(Coupon):
    threshold: float = 0.0
    discount_amount: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.threshold < 0:
            raise InvalidCouponError("threshold cannot be negative")
        if self.discount_amount <= 0:
            raise InvalidCouponError("discount_amount must be positive")

    @property
    def coupon_type(self) -> CouponType:
        return CouponType.FIXED_AMOUNT

    def _calculate_raw_discount(self, amount: float) -> float:
        if amount < self.threshold:
            return 0.0
        return self.discount_amount


@dataclass
class PercentageCoupon(Coupon):
    threshold: float = 0.0
    discount_rate: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.threshold < 0:
            raise InvalidCouponError("threshold cannot be negative")
        if self.discount_rate <= 0 or self.discount_rate > 1:
            raise InvalidCouponError("discount_rate must be in (0, 1]")

    @property
    def coupon_type(self) -> CouponType:
        return CouponType.PERCENTAGE

    def _calculate_raw_discount(self, amount: float) -> float:
        if amount < self.threshold:
            return 0.0
        return amount * self.discount_rate


@dataclass
class TieredCoupon(Coupon):
    tiers: List[Tier] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.tiers:
            raise InvalidCouponError("TieredCoupon must have at least one tier")
        sorted_tiers = sorted(self.tiers, key=lambda t: t.min_amount)
        for i in range(len(sorted_tiers) - 1):
            if sorted_tiers[i].max_amount is None:
                raise InvalidCouponError("Only the last tier can have max_amount=None")
            if sorted_tiers[i + 1].min_amount < sorted_tiers[i].max_amount:
                raise InvalidCouponError("Tiers must not overlap and must be contiguous")
        self.tiers = sorted_tiers

    @property
    def coupon_type(self) -> CouponType:
        return CouponType.TIERED

    def _calculate_raw_discount(self, amount: float) -> float:
        for tier in self.tiers:
            if tier.max_amount is None:
                if amount >= tier.min_amount:
                    matched = tier
                    break
            else:
                if tier.min_amount <= amount < tier.max_amount:
                    matched = tier
                    break
        else:
            return 0.0
        if matched.discount_type == TierDiscountType.FIXED_AMOUNT:
            return matched.discount_value
        else:
            return amount * matched.discount_value


@dataclass
class CouponDetail:
    coupon_id: str
    coupon_name: str
    coupon_type: CouponType
    applied: bool
    excluded_by_mutex: bool
    excluded_by_expiry: bool
    excluded_by_threshold: bool
    discount_amount: float
    amount_before: float
    amount_after: float
    capped: bool
    exclusion_reason: Optional[str] = None


@dataclass
class CalculationResult:
    original_amount: float
    final_amount: float
    total_discount: float
    global_capped: bool
    details: List[CouponDetail]
